import csv

from django.db.models import Avg, Count, F
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, GateAssignment, ServiceRequest, User
from .permissions import IsAdmin, IsStaffRole
from .serializers import AuditLogSerializer


class GateAssignmentReportView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        from_date = parse_date(request.query_params.get("from_date", ""))
        to_date = parse_date(request.query_params.get("to_date", ""))
        gate_number = request.query_params.get("gate_number")
        export = request.query_params.get("export") == "csv"

        if not from_date or not to_date:
            return Response({"message": "from_date and to_date (YYYY-MM-DD) are required."}, status=422)

        qs = GateAssignment.objects.filter(
            is_deleted=False, start_time__date__gte=from_date, start_time__date__lte=to_date
        ).select_related("gate", "flight").order_by("start_time__date", "gate__gate_number")
        if gate_number:
            qs = qs.filter(gate__gate_number=gate_number)

        rows = []
        for a in qs:
            duration = (a.end_time - a.start_time)
            rows.append({
                "date": a.start_time.date().isoformat(),
                "gate_number": a.gate.gate_number,
                "flight_no": a.flight.flight_no,
                "airline": a.flight.airline,
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "duration_minutes": int(duration.total_seconds() // 60),
                "status": a.status,
            })

        if export:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=gate_assignment_report.csv"
            writer = csv.writer(response)
            writer.writerow(["Date", "Gate Number", "Flight Number", "Airline", "Start", "End", "Duration (min)", "Status"])
            for r in rows:
                writer.writerow([r["date"], r["gate_number"], r["flight_no"], r["airline"], r["start_time"], r["end_time"], r["duration_minutes"], r["status"]])
            return response

        return Response({"count": len(rows), "results": rows})


class ServiceRequestAnalyticsView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        qs = ServiceRequest.objects.all()
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        category = request.query_params.get("category")
        status_filter = request.query_params.get("status")

        if from_date:
            qs = qs.filter(created_at__date__gte=parse_date(from_date))
        if to_date:
            qs = qs.filter(created_at__date__lte=parse_date(to_date))
        if category:
            qs = qs.filter(category=category)
        if status_filter:
            qs = qs.filter(status=status_filter)

        total = qs.count()
        resolved_qs = qs.filter(status=ServiceRequest.Status.RESOLVED)
        total_resolved = resolved_qs.count()
        total_open = qs.filter(status=ServiceRequest.Status.OPEN).count()

        avg_resolution_seconds = resolved_qs.exclude(resolved_at=None).annotate(
            resolution_time=F("resolved_at") - F("created_at")
        ).aggregate(avg=Avg("resolution_time"))["avg"]
        avg_resolution_minutes = (
            round(avg_resolution_seconds.total_seconds() / 60, 1) if avg_resolution_seconds else None
        )

        category_breakdown = list(qs.values("category").annotate(count=Count("id")).order_by("-count"))
        status_breakdown = list(qs.values("status").annotate(count=Count("id")).order_by("-count"))
        staff_breakdown = list(
            qs.exclude(assigned_to=None)
            .values("assigned_to__id", "assigned_to__username")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response({
            "total_requests": total,
            "total_resolved": total_resolved,
            "total_open": total_open,
            "open_vs_resolved_ratio": round(total_open / total_resolved, 2) if total_resolved else None,
            "average_resolution_minutes": avg_resolution_minutes,
            "category_breakdown": category_breakdown,
            "status_breakdown": status_breakdown,
            "staff_breakdown": staff_breakdown,
        })


class AuditLogListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AuditLog.objects.select_related("user").order_by("-timestamp")[:500]
        return Response(AuditLogSerializer(qs, many=True).data)


class GroundStaffListView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        staff = User.objects.filter(role=User.Role.GROUND_STAFF, is_active=True).order_by("username")
        return Response([{"id": u.id, "username": u.username, "email": u.email} for u in staff])
