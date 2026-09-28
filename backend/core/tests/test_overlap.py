from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.exceptions import UnprocessableEntity
from core.models import Flight, Gate, GateAssignment, User
from core.services import ConflictError, check_gate_overlap, create_gate_assignment


class GateOverlapBufferTests(TestCase):
    def setUp(self):
        self.controller = User.objects.create_user(
            username="controller1", email="c1@x.com", password="pass12345", role=User.Role.GATE_CONTROLLER
        )
        self.gate = Gate.objects.create(
            gate_number="B12", terminal="B", gate_type=Gate.GateType.DOMESTIC, status=Gate.Status.OPERATIONAL
        )
        self.now = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.flight_a = Flight.objects.create(
            flight_no="FLA001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        self.flight_b = Flight.objects.create(
            flight_no="FLB002", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        # Flight A occupies gate 12:00 - 14:00
        create_gate_assignment(
            gate_id=self.gate.id, flight=self.flight_a,
            start_time=self.now, end_time=self.now + timedelta(hours=2),
            assigned_by=self.controller,
        )

    def test_exact_overlap_rejected(self):
        with self.assertRaises(ConflictError):
            check_gate_overlap(self.gate, self.now, self.now + timedelta(hours=1))

    def test_buffer_violation_14_00_end_14_20_start(self):
        # existing ends at +2h (14:00 analog); new request starts at +2h20m -> violates 30 min buffer
        start = self.now + timedelta(hours=2, minutes=20)
        end = start + timedelta(hours=1)
        with self.assertRaises(ConflictError):
            check_gate_overlap(self.gate, start, end)

    def test_buffer_satisfied_14_00_end_14_30_start(self):
        start = self.now + timedelta(hours=2, minutes=30)
        end = start + timedelta(hours=1)
        # Should NOT raise
        check_gate_overlap(self.gate, start, end)

    def test_gate_type_mismatch(self):
        intl_gate = Gate.objects.create(
            gate_number="I1", terminal="I", gate_type=Gate.GateType.INTERNATIONAL, status=Gate.Status.OPERATIONAL
        )
        with self.assertRaises(UnprocessableEntity):
            create_gate_assignment(
                gate_id=intl_gate.id, flight=self.flight_b,
                start_time=self.now + timedelta(hours=5), end_time=self.now + timedelta(hours=6),
                assigned_by=self.controller,
            )

    def test_maintenance_lock(self):
        maint_gate = Gate.objects.create(
            gate_number="M1", terminal="M", gate_type=Gate.GateType.DOMESTIC, status=Gate.Status.UNDER_MAINTENANCE
        )
        with self.assertRaises(UnprocessableEntity):
            create_gate_assignment(
                gate_id=maint_gate.id, flight=self.flight_b,
                start_time=self.now + timedelta(hours=5), end_time=self.now + timedelta(hours=6),
                assigned_by=self.controller,
            )

    def test_non_overlapping_far_apart_accepted(self):
        start = self.now + timedelta(hours=10)
        end = start + timedelta(hours=1)
        check_gate_overlap(self.gate, start, end)
