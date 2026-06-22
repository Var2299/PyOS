from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allows access only to users flagged as application admins or Django staff."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_admin_role or user.is_staff))
