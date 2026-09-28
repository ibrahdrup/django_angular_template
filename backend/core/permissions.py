from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """Grants access only to authenticated users whose role is in `allowed_roles`.

    Returns 401 (via IsAuthenticated failing first) for unauthenticated requests,
    and 403 with 'Insufficient permissions.' for authenticated users with the wrong role.
    """

    allowed_roles = ()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in self.allowed_roles


def role_permission(*roles):
    return type(
        f"RolePermission_{'_'.join(roles)}",
        (HasRole,),
        {"allowed_roles": roles},
    )


IsAdmin = role_permission("admin")
IsGateController = role_permission("gate_controller")
IsGroundStaff = role_permission("ground_staff")
IsPassenger = role_permission("passenger")
IsAdminOrGateController = role_permission("admin", "gate_controller")
IsAdminOrGroundStaff = role_permission("admin", "ground_staff")
IsStaffRole = role_permission("admin", "gate_controller", "ground_staff")
IsGroundStaffOrGateControllerOrAdmin = role_permission("admin", "gate_controller", "ground_staff")
