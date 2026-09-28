from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        GATE_CONTROLLER = "gate_controller", "Gate Controller"
        GROUND_STAFF = "ground_staff", "Ground Staff"
        PASSENGER = "passenger", "Passenger"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PASSENGER, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"


class Gate(models.Model):
    class GateType(models.TextChoices):
        DOMESTIC = "domestic", "Domestic"
        INTERNATIONAL = "international", "International"
        CARGO = "cargo", "Cargo"

    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        UNDER_MAINTENANCE = "under_maintenance", "Under Maintenance"
        CLOSED = "closed", "Closed"

    gate_number = models.CharField(max_length=10, unique=True)
    terminal = models.CharField(max_length=50)
    gate_type = models.CharField(max_length=20, choices=GateType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPERATIONAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.gate_number


class Flight(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ASSIGNED = "assigned", "Assigned"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        CANCELLED = "cancelled", "Cancelled"
        ARRIVED = "arrived", "Arrived"

    flight_no = models.CharField(max_length=10, unique=True, db_index=True)
    airline = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    aircraft_type = models.CharField(max_length=50)
    scheduled_arrival = models.DateTimeField()
    scheduled_departure = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    flight_type = models.CharField(
        max_length=20,
        choices=Gate.GateType.choices,
        default=Gate.GateType.DOMESTIC,
        help_text="Determines which gate types this flight may be assigned to.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.flight_no


class GateAssignment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ASSIGNED = "assigned", "Assigned"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        CANCELLED = "cancelled", "Cancelled"

    gate = models.ForeignKey(Gate, on_delete=models.CASCADE, related_name="assignments")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="gate_assignments")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assignments_made"
    )
    notes = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["gate", "start_time", "end_time"], name="idx_gate_start_end"),
            models.Index(fields=["gate", "start_time"], name="idx_gate_start"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")),
                name="gate_assignment_start_before_end",
            )
        ]

    def __str__(self):
        return f"{self.flight.flight_no} @ {self.gate.gate_number}"


class ServiceRequest(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", "Food"
        BEVERAGE = "beverage", "Beverage"
        WHEELCHAIR = "wheelchair", "Wheelchair"
        SPECIAL_ASSISTANCE = "special_assistance", "Special Assistance"
        MEDICAL = "medical", "Medical"
        LOST_BAGGAGE = "lost_baggage", "Lost Baggage"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_requests")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="service_requests")
    flight_no = models.CharField(max_length=10)
    category = models.CharField(max_length=30, choices=Category.choices)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_requests"
    )
    resolution_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["passenger", "status"], name="idx_passenger_status"),
        ]

    def __str__(self):
        return f"SR#{self.id} {self.category} ({self.status})"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
