from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .exceptions import UnprocessableEntity
from .models import AuditLog, Gate, GateAssignment, ServiceRequest

BUFFER_MINUTES = 30


class ConflictError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def log_audit(user, action, entity_type, entity_id, details=""):
    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
    )


def check_gate_overlap(gate, start_time, end_time, exclude_assignment_id=None):
    """Reusable overlap check with the mandatory 30-minute turnaround buffer.

    Overlap formula: start_time < existing.end_time AND end_time > existing.start_time,
    applied to a window widened by BUFFER_MINUTES on each side of the *existing* assignment.
    Raises ConflictError if an overlapping/buffer-violating assignment exists on the gate.
    Must be called inside a transaction with the gate row locked (select_for_update).
    """
    buffer = timedelta(minutes=BUFFER_MINUTES)
    qs = GateAssignment.objects.filter(
        gate=gate, is_deleted=False
    ).exclude(status=GateAssignment.Status.CANCELLED)
    if exclude_assignment_id:
        qs = qs.exclude(id=exclude_assignment_id)

    for existing in qs:
        widened_start = existing.start_time - buffer
        widened_end = existing.end_time + buffer
        if start_time < widened_end and end_time > widened_start:
            raise ConflictError(
                f"Gate {gate.gate_number} is already occupied during this time period "
                f"(30-minute buffer required)."
            )


@transaction.atomic
def create_gate_assignment(gate_id, flight, start_time, end_time, assigned_by, notes="", override=False):
    gate = Gate.objects.select_for_update().get(id=gate_id)

    if not override:
        if gate.status != Gate.Status.OPERATIONAL:
            raise UnprocessableEntity("Gate is currently unavailable for assignment.")

        if flight.flight_type != gate.gate_type:
            raise UnprocessableEntity("Gate type does not match flight type.")

        check_gate_overlap(gate, start_time, end_time)

    assignment = GateAssignment.objects.create(
        gate=gate,
        flight=flight,
        start_time=start_time,
        end_time=end_time,
        status=GateAssignment.Status.ASSIGNED,
        assigned_by=assigned_by,
        notes=notes,
    )

    if flight.status == flight.Status.SCHEDULED:
        flight.status = flight.Status.ASSIGNED
        flight.save(update_fields=["status", "updated_at"])

    action = "gate_assignment_override_create" if override else "gate_assignment_create"
    log_audit(
        assigned_by, action, "gate_assignment", assignment.id,
        details=f"Assigned flight {flight.flight_no} to gate {gate.gate_number} "
                f"{start_time.isoformat()} - {end_time.isoformat()}" + (" [OVERRIDE]" if override else ""),
    )
    return assignment


@transaction.atomic
def update_gate_assignment(assignment, data, updated_by, override=False):
    gate_id = data.get("gate", assignment.gate_id)
    gate = Gate.objects.select_for_update().get(id=gate_id)
    start_time = data.get("start_time", assignment.start_time)
    end_time = data.get("end_time", assignment.end_time)
    flight = data.get("flight", assignment.flight)

    if not override:
        if gate.status != Gate.Status.OPERATIONAL:
            raise UnprocessableEntity("Gate is currently unavailable for assignment.")
        if flight.flight_type != gate.gate_type:
            raise UnprocessableEntity("Gate type does not match flight type.")
        check_gate_overlap(gate, start_time, end_time, exclude_assignment_id=assignment.id)

    for field in ["gate", "flight", "start_time", "end_time", "notes", "status"]:
        if field in data:
            setattr(assignment, field, data[field])
    assignment.save()

    action = "gate_assignment_override_update" if override else "gate_assignment_update"
    log_audit(updated_by, action, "gate_assignment", assignment.id, details=str(data))
    return assignment


def soft_delete_gate_assignment(assignment, deleted_by):
    assignment.is_deleted = True
    assignment.save(update_fields=["is_deleted", "updated_at"])
    log_audit(deleted_by, "gate_assignment_delete", "gate_assignment", assignment.id,
              details="Soft deleted")
    return assignment


# --- Flight state machine -------------------------------------------------

FLIGHT_TRANSITIONS = {
    "scheduled": {"assigned", "boarding", "cancelled"},
    "assigned": {"delayed", "boarding", "cancelled"},
    "delayed": {"assigned", "cancelled", "boarding"},
    "boarding": {"departed", "cancelled"},
    "departed": set(),
    "cancelled": {"scheduled"},
    "arrived": {"cancelled"},
}


def transition_flight_status(flight, new_status):
    current = flight.status
    if current == "departed":
        raise UnprocessableEntity("Cannot modify departed flight.")
    if current == "cancelled" and new_status != "scheduled":
        raise UnprocessableEntity("Cancelled flights must be rescheduled before reassignment.")
    if new_status not in FLIGHT_TRANSITIONS.get(current, set()):
        raise UnprocessableEntity(f"Invalid state transition: {current} -> {new_status}.")

    flight.status = new_status
    flight.save(update_fields=["status", "updated_at"])

    if new_status == "departed":
        cascade_departure_release(flight)

    return flight


@transaction.atomic
def cascade_departure_release(flight):
    GateAssignment.objects.filter(
        flight=flight, is_deleted=False
    ).exclude(status=GateAssignment.Status.CANCELLED).update(status=GateAssignment.Status.DEPARTED)

    ServiceRequest.objects.filter(
        flight=flight, status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_PROGRESS]
    ).update(
        status=ServiceRequest.Status.RESOLVED,
        resolution_notes="Flight departed — auto resolved.",
        resolved_at=timezone.now(),
    )


# --- Service request state machine ----------------------------------------

SERVICE_REQUEST_TRANSITIONS = {
    "open": {"in_progress", "rejected"},
    "in_progress": {"resolved", "rejected"},
    "resolved": set(),
    "rejected": set(),
}


def transition_service_request_status(service_request, new_status):
    current = service_request.status
    if current == "resolved":
        raise UnprocessableEntity("Cannot reopen a resolved request.")
    if current == "rejected":
        raise UnprocessableEntity("Cannot reopen a rejected request.")
    if new_status not in SERVICE_REQUEST_TRANSITIONS.get(current, set()):
        raise UnprocessableEntity(f"Invalid state transition: {current} -> {new_status}.")

    service_request.status = new_status
    if new_status in ("resolved", "rejected"):
        service_request.resolved_at = timezone.now()
    service_request.save()
    return service_request
