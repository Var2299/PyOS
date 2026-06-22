from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model so we can extend it later without a painful migration."""

    is_admin_role = models.BooleanField(
        default=False,
        help_text="Application-level admin flag (separate from Django staff/superuser).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
