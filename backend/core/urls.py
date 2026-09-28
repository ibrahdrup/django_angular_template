from django.urls import path

from . import views_assignments, views_auth, views_gates, views_reports, views_service_requests

urlpatterns = [
    # Auth
    path("auth/register", views_auth.RegisterView.as_view()),
    path("auth/login", views_auth.LoginView.as_view()),
    path("auth/logout", views_auth.LogoutView.as_view()),
    path("auth/refresh", views_auth.RefreshView.as_view()),

    # Admin user management
    path("admin/users", views_auth.UserListView.as_view()),
    path("admin/users/<int:user_id>/role", views_auth.UserRoleUpdateView.as_view()),
    path("admin/users/<int:user_id>/deactivate", views_auth.UserDeactivateView.as_view()),
    path("admin/audit-logs", views_reports.AuditLogListView.as_view()),

    # Gates
    path("gates", views_gates.GateListCreateView.as_view()),
    path("gates/<int:pk>", views_gates.GateDetailView.as_view()),

    # Flights
    path("flights", views_gates.FlightListCreateView.as_view()),
    path("flights/<int:pk>", views_gates.FlightDetailView.as_view()),
    path("flights/<int:pk>/status", views_gates.FlightStatusUpdateView.as_view()),

    # Gate assignments
    path("gate-assignments", views_assignments.GateAssignmentListCreateView.as_view()),
    path("gate-assignments/date/<str:date>", views_assignments.GateAssignmentByDateView.as_view()),
    path("gate-assignments/<int:pk>", views_assignments.GateAssignmentDetailView.as_view()),

    # Service requests
    path("service-requests", views_service_requests.ServiceRequestListCreateView.as_view()),
    path("service-requests/<int:pk>", views_service_requests.ServiceRequestDetailUpdateView.as_view()),

    # Reports
    path("reports/gate-assignments", views_reports.GateAssignmentReportView.as_view()),
    path("reports/service-requests", views_reports.ServiceRequestAnalyticsView.as_view()),
    path("staff/ground-staff", views_reports.GroundStaffListView.as_view()),
]
