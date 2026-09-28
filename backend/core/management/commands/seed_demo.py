from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Flight, Gate, GateAssignment, ServiceRequest, User


class Command(BaseCommand):
    help = "Seed demo data: one user per role, gates, flights, and gate assignments."

    def handle(self, *args, **options):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        admin, _ = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@airportops.local", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True}
        )
        admin.set_password("Admin@12345")
        admin.role = User.Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        controller, _ = User.objects.get_or_create(
            username="gatecontroller", defaults={"email": "controller@airportops.local", "role": User.Role.GATE_CONTROLLER}
        )
        controller.set_password("Controller@12345")
        controller.role = User.Role.GATE_CONTROLLER
        controller.save()

        ground_staff, _ = User.objects.get_or_create(
            username="groundstaff", defaults={"email": "groundstaff@airportops.local", "role": User.Role.GROUND_STAFF}
        )
        ground_staff.set_password("GroundStaff@12345")
        ground_staff.role = User.Role.GROUND_STAFF
        ground_staff.save()

        passenger, _ = User.objects.get_or_create(
            username="passenger", defaults={"email": "passenger@airportops.local", "role": User.Role.PASSENGER}
        )
        passenger.set_password("Passenger@12345")
        passenger.role = User.Role.PASSENGER
        passenger.save()

        gates_data = [
            ("A1", "Terminal A", Gate.GateType.DOMESTIC, Gate.Status.OPERATIONAL),
            ("A2", "Terminal A", Gate.GateType.DOMESTIC, Gate.Status.OPERATIONAL),
            ("B1", "Terminal B", Gate.GateType.INTERNATIONAL, Gate.Status.OPERATIONAL),
            ("B2", "Terminal B", Gate.GateType.INTERNATIONAL, Gate.Status.UNDER_MAINTENANCE),
            ("C1", "Terminal C", Gate.GateType.CARGO, Gate.Status.OPERATIONAL),
        ]
        gates = {}
        for number, terminal, gtype, gstatus in gates_data:
            gate, _ = Gate.objects.get_or_create(
                gate_number=number,
                defaults={"terminal": terminal, "gate_type": gtype, "status": gstatus},
            )
            gates[number] = gate

        flights_data = [
            ("AA123", "American Airlines", "JFK", "LAX", "Boeing 737", Gate.GateType.DOMESTIC, 2, 4),
            ("BA456", "British Airways", "LHR", "JFK", "Boeing 777", Gate.GateType.INTERNATIONAL, 3, 6),
            ("CG789", "CargoJet", "ORD", "MIA", "Boeing 767F", Gate.GateType.CARGO, 5, 8),
            ("DL234", "Delta", "ATL", "SEA", "Airbus A320", Gate.GateType.DOMESTIC, 6, 9),
        ]
        flights = {}
        for flight_no, airline, origin, dest, aircraft, ftype, arr_h, dep_h in flights_data:
            flight, _ = Flight.objects.get_or_create(
                flight_no=flight_no,
                defaults={
                    "airline": airline,
                    "origin": origin,
                    "destination": dest,
                    "aircraft_type": aircraft,
                    "flight_type": ftype,
                    "scheduled_arrival": now + timedelta(hours=arr_h),
                    "scheduled_departure": now + timedelta(hours=dep_h),
                    "status": Flight.Status.SCHEDULED,
                },
            )
            flights[flight_no] = flight

        if not GateAssignment.objects.filter(flight=flights["AA123"]).exists():
            GateAssignment.objects.create(
                gate=gates["A1"], flight=flights["AA123"],
                start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=3, minutes=30),
                status=GateAssignment.Status.ASSIGNED, assigned_by=controller,
                notes="Seeded assignment",
            )
            flights["AA123"].status = Flight.Status.ASSIGNED
            flights["AA123"].save()

        if not GateAssignment.objects.filter(flight=flights["BA456"]).exists():
            GateAssignment.objects.create(
                gate=gates["B1"], flight=flights["BA456"],
                start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=5),
                status=GateAssignment.Status.ASSIGNED, assigned_by=controller,
                notes="Seeded assignment",
            )
            flights["BA456"].status = Flight.Status.ASSIGNED
            flights["BA456"].save()

        if not ServiceRequest.objects.filter(passenger=passenger).exists():
            ServiceRequest.objects.create(
                passenger=passenger, flight=flights["AA123"], flight_no="AA123",
                category=ServiceRequest.Category.WHEELCHAIR,
                details="Need wheelchair assistance at gate.",
                status=ServiceRequest.Status.OPEN,
            )
            ServiceRequest.objects.create(
                passenger=passenger, flight=flights["BA456"], flight_no="BA456",
                category=ServiceRequest.Category.LOST_BAGGAGE,
                details="Lost a carry-on bag near check-in.",
                status=ServiceRequest.Status.IN_PROGRESS,
                assigned_to=ground_staff,
            )

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))
        self.stdout.write("Login credentials:")
        self.stdout.write("  admin / Admin@12345")
        self.stdout.write("  gatecontroller / Controller@12345")
        self.stdout.write("  groundstaff / GroundStaff@12345")
        self.stdout.write("  passenger / Passenger@12345")
