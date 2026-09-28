from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Flight, Gate, User


class AuthApiTests(APITestCase):
    def test_register_creates_passenger_only(self):
        resp = self.client.post("/api/v1/auth/register", {
            "username": "newpax", "email": "newpax@x.com", "password": "StrongPass123",
        })
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(username="newpax")
        self.assertEqual(user.role, "passenger")

    def test_duplicate_email_returns_409(self):
        User.objects.create_user(username="dupuser", email="dup@x.com", password="pass12345")
        resp = self.client.post("/api/v1/auth/register", {
            "username": "dupuser2", "email": "dup@x.com", "password": "StrongPass123",
        })
        self.assertEqual(resp.status_code, 409)

    def test_login_success_and_payload(self):
        User.objects.create_user(username="loginuser", email="login@x.com", password="pass12345", role="passenger")
        resp = self.client.post("/api/v1/auth/login", {"username": "loginuser", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["role"], "passenger")

    def test_login_invalid_credentials_401(self):
        resp = self.client.post("/api/v1/auth/login", {"username": "nouser", "password": "bad"})
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_request_401(self):
        resp = self.client.get("/api/v1/gate-assignments")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_role_403(self):
        User.objects.create_user(username="pax3", email="pax3@x.com", password="pass12345", role="passenger")
        login = self.client.post("/api/v1/auth/login", {"username": "pax3", "password": "pass12345"})
        token = login.data["access"]
        resp = self.client.post(
            "/api/v1/gate-assignments", {},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data["message"], "Insufficient permissions.")


class ServiceRequestApiTests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.passenger = User.objects.create_user(
            username="paxsr", email="paxsr@x.com", password="pass12345", role="passenger"
        )
        self.flight = Flight.objects.create(
            flight_no="APX001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        login = self.client.post("/api/v1/auth/login", {"username": "paxsr", "password": "pass12345"})
        self.token = login.data["access"]

    def test_unknown_flight_no_404(self):
        resp = self.client.post(
            "/api/v1/service-requests",
            {"flight_no": "NOPE999", "category": "food", "details": "test"},
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data["message"], "Flight not found.")

    def test_invalid_category_422(self):
        resp = self.client.post(
            "/api/v1/service-requests",
            {"flight_no": self.flight.flight_no, "category": "not_a_category", "details": "test"},
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 422)

    def test_create_success_sets_passenger_from_jwt(self):
        resp = self.client.post(
            "/api/v1/service-requests",
            {"flight_no": self.flight.flight_no, "category": "food", "details": "vegetarian meal"},
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["passenger"], self.passenger.id)


class GateAssignmentApiTests(APITestCase):
    def setUp(self):
        self.now = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.controller = User.objects.create_user(
            username="ctrlapi", email="ctrlapi@x.com", password="pass12345", role="gate_controller"
        )
        self.gate = Gate.objects.create(
            gate_number="G1", terminal="G", gate_type=Gate.GateType.DOMESTIC, status=Gate.Status.OPERATIONAL
        )
        self.maint_gate = Gate.objects.create(
            gate_number="G2", terminal="G", gate_type=Gate.GateType.DOMESTIC, status=Gate.Status.UNDER_MAINTENANCE
        )
        self.intl_gate = Gate.objects.create(
            gate_number="G3", terminal="G", gate_type=Gate.GateType.INTERNATIONAL, status=Gate.Status.OPERATIONAL
        )
        self.flight = Flight.objects.create(
            flight_no="GAPI001", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        self.flight2 = Flight.objects.create(
            flight_no="GAPI002", airline="TestAir", origin="X", destination="Y", aircraft_type="A320",
            flight_type=Gate.GateType.DOMESTIC,
            scheduled_arrival=self.now, scheduled_departure=self.now + timedelta(hours=2),
        )
        login = self.client.post("/api/v1/auth/login", {"username": "ctrlapi", "password": "pass12345"})
        self.token = login.data["access"]

    def _post(self, payload):
        return self.client.post(
            "/api/v1/gate-assignments", payload, HTTP_AUTHORIZATION=f"Bearer {self.token}", format="json"
        )

    def test_create_then_overlap_409(self):
        start = self.now.isoformat()
        end = (self.now + timedelta(hours=2)).isoformat()
        r1 = self._post({"gate": self.gate.id, "flight": self.flight.id, "start_time": start, "end_time": end})
        self.assertEqual(r1.status_code, 201)

        r2 = self._post({
            "gate": self.gate.id, "flight": self.flight2.id,
            "start_time": start, "end_time": end,
        })
        self.assertEqual(r2.status_code, 409)

    def test_maintenance_lock_422(self):
        start = self.now.isoformat()
        end = (self.now + timedelta(hours=1)).isoformat()
        resp = self._post({"gate": self.maint_gate.id, "flight": self.flight.id, "start_time": start, "end_time": end})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.data["message"], "Gate is currently unavailable for assignment.")

    def test_gate_type_mismatch_422(self):
        start = self.now.isoformat()
        end = (self.now + timedelta(hours=1)).isoformat()
        resp = self._post({"gate": self.intl_gate.id, "flight": self.flight.id, "start_time": start, "end_time": end})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.data["message"], "Gate type does not match flight type.")
