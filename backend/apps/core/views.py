from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.filesystem.commands import CommandEngine

from .models import ActivityLog, CommandHistory
from .serializers import ActivityLogSerializer, CommandHistorySerializer
from .utils import log_action


class ActivityLogListView(generics.ListAPIView):
   

    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        is_admin = user.is_admin_role or user.is_staff
        scope = self.request.query_params.get("scope", "all" if is_admin else "me")
        qs = ActivityLog.objects.select_related("user").all()
        if not is_admin or scope == "me":
            qs = qs.filter(user=user)
        return qs


class CommandHistoryListView(generics.ListCreateAPIView):
    serializer_class = CommandHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommandHistory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommandHistoryDetailView(generics.DestroyAPIView):
    serializer_class = CommandHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommandHistory.objects.filter(user=self.request.user)


class RunCommandView(APIView):
    """
    Execute a terminal command against the user's filesystem.

    Request body: { "command": "ls /home", "cwd": ["home", "alice"] }
    Response:     { "output": "...", "cwd": ["home", "alice"] }

    The command is run through the CommandEngine (the web port of the original
    PyOS CLI), recorded in the user's command history, and audited in the log
    when it mutates the filesystem.
    """

    permission_classes = [IsAuthenticated]

    MUTATING = {"mkdir", "touch", "echo", "rm", "chmod"}

    def post(self, request):
        command = (request.data.get("command") or "").strip()
        cwd = request.data.get("cwd") or []
        if not isinstance(cwd, list):
            cwd = []

        engine = CommandEngine(request.user, cwd=cwd)
        result = engine.execute(command)

        if command:
            # Record in history (mirrors the CLI's command_history).
            CommandHistory.objects.create(
                user=request.user, command=command, output=result.output
            )
            # Audit mutating commands in the activity log.
            verb = command.split()[0] if command.split() else ""
            if verb in self.MUTATING:
                log_action(request.user, "COMMAND", f"Ran: {command}")

        return Response({"output": result.output, "cwd": result.cwd})
