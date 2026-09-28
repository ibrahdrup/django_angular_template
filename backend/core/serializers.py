from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AuditLog, Flight, Gate, GateAssignment, ServiceRequest, User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "role": self.user.role,
        }
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            role=User.Role.PASSENGER,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_active", "created_at", "updated_at"]


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class GateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gate
        fields = ["id", "gate_number", "terminal", "gate_type", "status", "created_at", "updated_at"]


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = [
            "id", "flight_no", "airline", "origin", "destination", "aircraft_type",
            "flight_type", "scheduled_arrival", "scheduled_departure", "status",
            "created_at", "updated_at",
        ]


class GateAssignmentSerializer(serializers.ModelSerializer):
    gate_number = serializers.CharField(source="gate.gate_number", read_only=True)
    flight_no = serializers.CharField(source="flight.flight_no", read_only=True)
    assigned_by_username = serializers.CharField(source="assigned_by.username", read_only=True)

    class Meta:
        model = GateAssignment
        fields = [
            "id", "gate", "gate_number", "flight", "flight_no", "start_time", "end_time",
            "status", "assigned_by", "assigned_by_username", "notes", "is_deleted",
            "created_at", "updated_at",
        ]
        read_only_fields = ["assigned_by", "is_deleted"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError("start_time must be before end_time.")
        return attrs


class GateAssignmentCreateSerializer(serializers.Serializer):
    gate = serializers.PrimaryKeyRelatedField(queryset=Gate.objects.all())
    flight = serializers.PrimaryKeyRelatedField(queryset=Flight.objects.all())
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    override = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError("start_time must be before end_time.")
        return attrs


class ServiceRequestSerializer(serializers.ModelSerializer):
    passenger_username = serializers.CharField(source="passenger.username", read_only=True)
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True, default=None)

    class Meta:
        model = ServiceRequest
        fields = [
            "id", "passenger", "passenger_username", "flight", "flight_no", "category",
            "details", "status", "assigned_to", "assigned_to_username", "resolution_notes",
            "created_at", "updated_at", "resolved_at",
        ]
        read_only_fields = ["passenger", "flight", "flight_no", "status", "created_at", "updated_at", "resolved_at"]


class ServiceRequestCreateSerializer(serializers.Serializer):
    flight_no = serializers.CharField()
    category = serializers.ChoiceField(choices=ServiceRequest.Category.choices)
    details = serializers.CharField(required=False, allow_blank=True, default="")


class ServiceRequestUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ServiceRequest.Status.choices, required=False)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.GROUND_STAFF), required=False, allow_null=True
    )
    resolution_notes = serializers.CharField(required=False, allow_blank=True)


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "user", "username", "action", "entity_type", "entity_id", "details", "timestamp"]
