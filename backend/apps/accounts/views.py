from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, Length
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.utils import log_action

from .permissions import IsAdminRole
from .serializers import AdminUserSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


def annotate_usage(queryset):
    """Annotate users with file/dir counts and total content size (chars)."""
    active_files = Q(nodes__is_deleted=False, nodes__node_type="file")
    active_dirs = Q(nodes__is_deleted=False, nodes__node_type="directory")
    return queryset.annotate(
        files_created=Count("nodes", filter=active_files, distinct=True),
        directories_created=Count("nodes", filter=active_dirs, distinct=True),
        space_used=Coalesce(
            Sum(Length("nodes__content"), filter=active_files), 0
        ),
    )


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    """JWT login. Logs the action on success."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.filter(username=request.data.get("username")).first()
            if user:
                log_action(user, "LOGIN", f"User '{user.username}' logged in")
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserListView(generics.ListCreateAPIView):
    """Admin user-management dashboard: list all users with usage stats."""

    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return annotate_usage(User.objects.all()).order_by("id")

    def get_serializer_class(self):
        return RegisterSerializer if self.request.method == "POST" else AdminUserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: view, (de)activate, promote/revoke admin, or delete a user."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def update(self, request, *args, **kwargs):
        target = self.get_object()
        # Prevent an admin from demoting or deactivating their own account,
        # which would otherwise lock them out of the panel mid-session.
        if target.id == request.user.id:
            if request.data.get("is_admin_role") is False:
                raise PermissionDenied("You cannot revoke your own admin access.")
            if request.data.get("is_active") is False:
                raise PermissionDenied("You cannot deactivate your own account.")
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        before_admin = serializer.instance.is_admin_role
        before_active = serializer.instance.is_active
        user = serializer.save()
        # Keep Django's is_staff flag in sync with the app-level admin role so
        # both the app and the Django admin agree on who is an administrator.
        if user.is_admin_role != user.is_staff:
            user.is_staff = user.is_admin_role
            user.save(update_fields=["is_staff"])

        actor = self.request.user
        if user.is_admin_role != before_admin:
            verb = "Promoted" if user.is_admin_role else "Revoked admin from"
            log_action(actor, "USER_ROLE", f"{verb} user '{user.username}'")
        if user.is_active != before_active:
            state = "Activated" if user.is_active else "Deactivated"
            log_action(actor, "USER_UPDATE", f"{state} user '{user.username}'")

    def perform_destroy(self, instance):
        username = instance.username
        log_action(self.request.user, "USER_DELETE", f"Deleted user '{username}'")
        instance.delete()
