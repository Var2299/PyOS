from rest_framework import serializers

from .models import ActivityLog, CommandHistory


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = ["id", "username", "action", "detail", "created_at"]


class CommandHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandHistory
        fields = ["id", "command", "output", "created_at"]
        read_only_fields = ["id", "created_at"]
