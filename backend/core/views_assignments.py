from datetime import datetime

from django.db import transaction
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import UnprocessableEntity
from .models import Flight, Gate, GateAssignment
from .permissions import IsAdmin, IsAdminOrGateController, IsGroundStaffOrGateControllerOrAdmin
from .serializers import GateAssignmentCreateSerializer, GateAssignmentSerializer
from .services import ConflictError, create_gate_assignment, soft_delete_gate_assignment, update_gate_assignment


class GateAssignmentListCreateView(APIView):
    permission_classes = [IsAdminOrGateController]

    def get(self, request):
        qs = GateAssignment.objects.filter(is_deleted=False).select_related("gate", "flight", "assigned_by")
        gate_number = request.query_params.get("gate_number")
        if gate_number:
            qs = qs.filter(gate__gate_number=gate_number)
        return Response(GateAssignmentSerializer(qs.order_by("-start_time"), many=True).data)

    def post(self, request):
        serializer = GateAssignmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        data = serializer.validated_data
        override = data.get("override", False)
        if override and request.user.role != "admin":
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        try:
            with transaction.atomic():
                assignment = create_gate_assignment(
                    gate_id=data["gate"].id,
                    flight=data["flight"],
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    assigned_by=request.user,
                    notes=data.get("notes", ""),
                    override=override,
                )
        except UnprocessableEntity as exc:
            return Response({"message": exc.message}, status=422)
        except ConflictError as exc:
            return Response({"message": exc.message}, status=status.HTTP_409_CONFLICT)
        return Response(GateAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class GateAssignmentDetailView(APIView):
    permission_classes = [IsAdminOrGateController]

    def get_object(self, pk):
        try:
            return GateAssignment.objects.select_related("gate", "flight").get(id=pk, is_deleted=False)
        except GateAssignment.DoesNotExist:
            return None

    def get(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response({"message": "Gate assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(GateAssignmentSerializer(assignment).data)

    def patch(self, request, pk):
        assignment = self.get_object(pk)
        if not assignment:
            return Response({"message": "Gate assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        data = {}
        if "gate" in request.data:
            try:
                data["gate"] = Gate.objects.get(id=request.data["gate"])
            except Gate.DoesNotExist:
                return Response({"message": "Gate not found."}, status=status.HTTP_404_NOT_FOUND)
        if "flight" in request.data:
            try:
                data["flight"] = Flight.objects.get(id=request.data["flight"])
            except Flight.DoesNotExist:
                return Response({"message": "Flight not found."}, status=status.HTTP_404_NOT_FOUND)
        for field in ["start_time", "end_time", "notes", "status"]:
            if field in request.data:
                data[field] = request.data[field]

        if "start_time" in data and isinstance(data["start_time"], str):
            data["start_time"] = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
        if "end_time" in data and isinstance(data["end_time"], str):
            data["end_time"] = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))

        override = bool(request.data.get("override", False))
        if override and request.user.role != "admin":
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)

        try:
            with transaction.atomic():
                assignment = update_gate_assignment(assignment, data, request.user, override=override)
        except UnprocessableEntity as exc:
            return Response({"message": exc.message}, status=422)
        except ConflictError as exc:
            return Response({"message": exc.message}, status=status.HTTP_409_CONFLICT)
        return Response(GateAssignmentSerializer(assignment).data)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        assignment = self.get_object(pk)
        if not assignment:
            return Response({"message": "Gate assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        soft_delete_gate_assignment(assignment, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GateAssignmentByDateView(APIView):
    permission_classes = [IsGroundStaffOrGateControllerOrAdmin]

    def get(self, request, date):
        parsed = parse_date(date)
        if not parsed:
            return Response({"message": "Invalid date format. Use YYYY-MM-DD."}, status=422)
        qs = GateAssignment.objects.filter(
            is_deleted=False, start_time__date=parsed
        ).select_related("gate", "flight", "assigned_by").order_by("gate__gate_number", "start_time")
        return Response(GateAssignmentSerializer(qs, many=True).data)
