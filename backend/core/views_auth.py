from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    RoleUpdateSerializer,
    UserSerializer,
)
from .services import log_audit
from .throttles import LoginRateThrottle, RegisterRateThrottle


class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        if User.objects.filter(email__iexact=request.data.get("email", "")).exists():
            return Response({"message": "A user with this email already exists."}, status=status.HTTP_409_CONFLICT)
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = []
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"message": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"message": "refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"message": "Invalid or already-blacklisted token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class RefreshView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"message": "refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            access = str(token.access_token)
        except TokenError:
            return Response({"message": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"access": access}, status=status.HTTP_200_OK)


class UserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all().order_by("id")
        return Response(UserSerializer(users, many=True).data)


class UserRoleUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors}, status=422)
        old_role = user.role
        user.role = serializer.validated_data["role"]
        user.save(update_fields=["role", "updated_at"])
        log_audit(request.user, "role_change", "user", user.id, details=f"{old_role} -> {user.role}")
        return Response(UserSerializer(user).data)


class UserDeactivateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = bool(request.data.get("is_active", not user.is_active))
        user.save(update_fields=["is_active", "updated_at"])
        log_audit(request.user, "user_deactivate" if not user.is_active else "user_activate", "user", user.id)
        return Response(UserSerializer(user).data)
