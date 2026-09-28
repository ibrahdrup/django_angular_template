from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import exception_handler


class UnprocessableEntity(Exception):
    """Raised for business-rule state-machine / validation failures that map to HTTP 422."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def custom_exception_handler(exc, context):
    if isinstance(exc, UnprocessableEntity):
        return Response({"message": exc.message}, status=422)

    response = exception_handler(exc, context)

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return Response({"message": "Authentication credentials were not provided or are invalid."}, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, PermissionDenied):
        return Response({"message": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)

    return response
