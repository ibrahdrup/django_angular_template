from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import UnprocessableEntity
from .models import Flight, ServiceRequest, User
from .permissions import IsPassenger
from .serializers import (
    ServiceRequestCreateSerializer,
    ServiceRequestSerializer,
    ServiceRequestUpdateSerializer,
)
from .services import log_audit, transition_service_request_status


class ServiceRequestListCreateView(APIView):
    def get(self, request):
        qs = ServiceRequest.objects.select_related("passenger", "flight", "assigned_to")
        if request.user.role == "passenger":
            qs = qs.filter(passenger=request.user)
        status_filter = request.query_params.get("status")
        category_filter = request.query_params.get("category")
        flight_no_filter = request.query_params.get("flight_no")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)
        if flight_no_filter:
            qs = qs.filter(flight_no__iexact=flight_no_filter)
        return Response(ServiceRequestSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):
        if request.user.role != "passenger":
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ServiceRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        data = serializer.validated_data
        try:
            flight = Flight.objects.get(flight_no__iexact=data["flight_no"])
        except Flight.DoesNotExist:
            return Response({"message": "Flight not found."}, status=status.HTTP_404_NOT_FOUND)

        sr = ServiceRequest.objects.create(
            passenger=request.user,
            flight=flight,
            flight_no=flight.flight_no,
            category=data["category"],
            details=data.get("details", ""),
            status=ServiceRequest.Status.OPEN,
        )
        return Response(ServiceRequestSerializer(sr).data, status=status.HTTP_201_CREATED)


class ServiceRequestDetailUpdateView(APIView):
    def patch(self, request, pk):
        if request.user.role not in ("ground_staff", "admin"):
            return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)
        try:
            sr = ServiceRequest.objects.get(id=pk)
        except ServiceRequest.DoesNotExist:
            return Response({"message": "Service request not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServiceRequestUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        data = serializer.validated_data

        if "assigned_to" in data:
            sr.assigned_to = data["assigned_to"]
            sr.save(update_fields=["assigned_to", "updated_at"])

        if "resolution_notes" in data:
            sr.resolution_notes = data["resolution_notes"]
            sr.save(update_fields=["resolution_notes", "updated_at"])

        if "status" in data:
            try:
                sr = transition_service_request_status(sr, data["status"])
            except UnprocessableEntity as exc:
                return Response({"message": exc.message}, status=422)

        log_audit(request.user, "service_request_update", "service_request", sr.id, details=str(request.data))
        return Response(ServiceRequestSerializer(sr).data)
