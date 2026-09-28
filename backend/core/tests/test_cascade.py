from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import Flight, Gate, GateAssignment, ServiceRequest, User
from core.services import create_gate_assignment, transition_flight_status


class CascadingDepartureReleaseTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.controller = User.objects.create_user(
            username="controller2", email="c2@x.com", password="pass12345", role=User.Role.GATE_CONTROLLER
        )
        self.passenger = User.objects.create_user(
            username="pax2", email="pax2@x.com", password="pass12345", role=User.Role.PASSENGER
        )
        self.gate = Gate.objects.create(
            gate_number="D1", terminal="D", gate_type=Gate.GateType.DOMESTIC, status=Gate.Status.OPERATIONAL
        )
        self.flight = Flight.objects.create(
            flight_no="CD001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
            status="scheduled",
        )
        self.assignment = create_gate_assignment(
            gate_id=self.gate.id, flight=self.flight,
            start_time=self.now, end_time=self.now + timedelta(hours=2),
            assigned_by=self.controller,
        )
        self.sr = ServiceRequest.objects.create(
            passenger=self.passenger, flight=self.flight, flight_no=self.flight.flight_no,
            category=ServiceRequest.Category.FOOD, details="meal", status="open",
        )

    def test_departure_cascades(self):
        transition_flight_status(self.flight, "boarding")
        transition_flight_status(self.flight, "departed")

        self.flight.refresh_from_db()
        self.assignment.refresh_from_db()
        self.sr.refresh_from_db()

        self.assertEqual(self.flight.status, "departed")
        self.assertEqual(self.assignment.status, GateAssignment.Status.DEPARTED)
        self.assertEqual(self.sr.status, ServiceRequest.Status.RESOLVED)
        self.assertEqual(self.sr.resolution_notes, "Flight departed — auto resolved.")
        self.assertIsNotNone(self.sr.resolved_at)
