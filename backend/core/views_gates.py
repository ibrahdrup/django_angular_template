from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import UnprocessableEntity
from .models import Flight, Gate
from .permissions import IsAdmin, IsStaffRole
from .serializers import FlightSerializer, GateSerializer
from .services import log_audit, transition_flight_status


class GateListCreateView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        gates = Gate.objects.all().order_by("gate_number")
        return Response(GateSerializer(gates, many=True).data)

    def post(self, request):
        if request.user.role != "admin":
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        serializer = GateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        gate = serializer.save()
        log_audit(request.user, "gate_create", "gate", gate.id, details=str(request.data))
        return Response(GateSerializer(gate).data, status=status.HTTP_201_CREATED)


class GateDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            gate = Gate.objects.get(id=pk)
        except Gate.DoesNotExist:
            return Response({"message": "Gate not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = GateSerializer(gate, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        gate = serializer.save()
        log_audit(request.user, "gate_update", "gate", gate.id, details=str(request.data))
        return Response(GateSerializer(gate).data)


class FlightListCreateView(APIView):
    def get(self, request):
        flights = Flight.objects.all().order_by("-scheduled_departure")
        status_filter = request.query_params.get("status")
        if status_filter:
            flights = flights.filter(status=status_filter)
        return Response(FlightSerializer(flights, many=True).data)

    def post(self, request):
        if request.user.role not in ("admin", "gate_controller"):
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        serializer = FlightSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        flight = serializer.save()
        log_audit(request.user, "flight_create", "flight", flight.id, details=str(request.data))
        return Response(FlightSerializer(flight).data, status=status.HTTP_201_CREATED)


class FlightDetailView(APIView):
    def get(self, request, pk):
        try:
            flight = Flight.objects.get(id=pk)
        except Flight.DoesNotExist:
            return Response({"message": "Flight not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FlightSerializer(flight).data)


class FlightStatusUpdateView(APIView):
    def patch(self, request, pk):
        if request.user.role not in ("admin", "gate_controller"):
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        try:
            flight = Flight.objects.get(id=pk)
        except Flight.DoesNotExist:
            return Response({"message": "Flight not found."}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if not new_status:
            return Response({"message": "status is required."}, status=422)
        try:
            flight = transition_flight_status(flight, new_status)
        except UnprocessableEntity as exc:
            return Response({"message": exc.message}, status=422)
        log_audit(request.user, "flight_status_change", "flight", flight.id, details=f"-> {new_status}")
        return Response(FlightSerializer(flight).data)
