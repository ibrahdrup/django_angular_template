from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.exceptions import UnprocessableEntity
from core.models import Flight, Gate, ServiceRequest, User
from core.services import transition_flight_status, transition_service_request_status


class FlightStateMachineTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.flight = Flight.objects.create(
            flight_no="SM001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
            status="scheduled",
        )

    def test_scheduled_to_assigned_valid(self):
        transition_flight_status(self.flight, "assigned")
        self.assertEqual(self.flight.status, "assigned")

    def test_assigned_to_delayed_and_back(self):
        transition_flight_status(self.flight, "assigned")
        transition_flight_status(self.flight, "delayed")
        self.assertEqual(self.flight.status, "delayed")
        transition_flight_status(self.flight, "assigned")
        self.assertEqual(self.flight.status, "assigned")

    def test_boarding_to_departed(self):
        transition_flight_status(self.flight, "assigned")
        transition_flight_status(self.flight, "boarding")
        transition_flight_status(self.flight, "departed")
        self.assertEqual(self.flight.status, "departed")

    def test_departed_cannot_be_modified(self):
        transition_flight_status(self.flight, "assigned")
        transition_flight_status(self.flight, "boarding")
        transition_flight_status(self.flight, "departed")
        with self.assertRaises(UnprocessableEntity) as ctx:
            transition_flight_status(self.flight, "boarding")
        self.assertIn("Cannot modify departed flight.", str(ctx.exception.message))

    def test_cancelled_requires_reschedule(self):
        transition_flight_status(self.flight, "cancelled")
        with self.assertRaises(UnprocessableEntity) as ctx:
            transition_flight_status(self.flight, "boarding")
        self.assertIn("Cancelled flights must be rescheduled", ctx.exception.message)
        # Rescheduling back to scheduled is valid
        transition_flight_status(self.flight, "scheduled")
        self.assertEqual(self.flight.status, "scheduled")

    def test_any_state_to_cancelled_except_departed(self):
        transition_flight_status(self.flight, "cancelled")
        self.assertEqual(self.flight.status, "cancelled")


class ServiceRequestStateMachineTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.passenger = User.objects.create_user(
            username="pax1", email="pax1@x.com", password="pass12345", role=User.Role.PASSENGER
        )
        self.flight = Flight.objects.create(
            flight_no="SR001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        self.sr = ServiceRequest.objects.create(
            passenger=self.passenger, flight=self.flight, flight_no=self.flight.flight_no,
            category=ServiceRequest.Category.WHEELCHAIR, details="test", status="open",
        )

    def test_open_to_in_progress(self):
        transition_service_request_status(self.sr, "in_progress")
        self.assertEqual(self.sr.status, "in_progress")

    def test_in_progress_to_resolved_sets_resolved_at(self):
        transition_service_request_status(self.sr, "in_progress")
        transition_service_request_status(self.sr, "resolved")
        self.assertEqual(self.sr.status, "resolved")
        self.assertIsNotNone(self.sr.resolved_at)

    def test_open_to_rejected_valid(self):
        transition_service_request_status(self.sr, "rejected")
        self.assertEqual(self.sr.status, "rejected")

    def test_resolved_cannot_reopen(self):
        transition_service_request_status(self.sr, "in_progress")
        transition_service_request_status(self.sr, "resolved")
        with self.assertRaises(UnprocessableEntity):
            transition_service_request_status(self.sr, "open")

    def test_rejected_cannot_reopen(self):
        transition_service_request_status(self.sr, "rejected")
        with self.assertRaises(UnprocessableEntity):
            transition_service_request_status(self.sr, "in_progress")
