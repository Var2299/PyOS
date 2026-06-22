from django.conf import settings
from django.db import models


class Node(models.Model):
   

    DIRECTORY = "directory"
    FILE = "file"
    NODE_TYPES = [(DIRECTORY, "Directory"), (FILE, "File")]

    # Access control. PRIVATE: only the owner. READ_ONLY: any logged-in user can
    # view but not modify. PUBLIC: any logged-in user can view and edit content.
    PRIVATE = "private"
    READ_ONLY = "read_only"
    PUBLIC = "public"
    PERMISSION_LEVELS = [
        (PRIVATE, "Private"),
        (READ_ONLY, "Read-only"),
        (PUBLIC, "Public"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=16, choices=NODE_TYPES)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    content = models.TextField(blank=True, default="")
    permission_level = models.CharField(
        max_length=16,
        choices=PERMISSION_LEVELS,
        default=PRIVATE,
        help_text="Controls whether other logged-in users can see/edit this node.",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["node_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "parent", "name", "is_deleted"],
                name="unique_name_per_directory",
            )
        ]

    def __str__(self):
        return self.path

    @property
    def path(self):
        parts = [self.name]
        node = self.parent
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    @property
    def is_directory(self):
        return self.node_type == self.DIRECTORY

    @property
    def is_protected(self):
        """System directories that cannot be deleted (like /home in a real OS).

        Two things are protected, mirroring a real OS where you can delete
        neither /home nor your own /home/<username>:
          1. The top-level 'home' directory (parent is null, name 'home').
          2. The user's own home directory 'home/<username>' (its parent is the
             top-level home and its name equals the owner's username).
        Everything inside the user's home remains freely removable.
        """
        if self.parent_id is None and self.name == "home":
            return True
        parent = self.parent
        if (
            parent is not None
            and parent.parent_id is None
            and parent.name == "home"
            and self.name == self.owner.username
        ):
            return True
        return False
