from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """Append-only audit log of meaningful actions in the system."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=64)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"


class CommandHistory(models.Model):
    """Stores commands a user runs in the PyOS terminal/explorer."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commands",
    )
    command = models.CharField(max_length=512)
    output = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.command
