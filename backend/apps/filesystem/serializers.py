from rest_framework import serializers

from .models import Node


class NodeSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    children_count = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    # True when the requesting user can modify this node (owner, admin, or public).
    can_edit = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_protected = serializers.BooleanField(read_only=True)

    class Meta:
        model = Node
        fields = [
            "id",
            "name",
            "node_type",
            "parent",
            "path",
            "content",
            "permission_level",
            "owner_username",
            "is_owner",
            "can_edit",
            "is_protected",
            "is_deleted",
            "deleted_at",
            "children_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
            "owner_username",
        ]

    def get_children_count(self, obj):
        if obj.node_type == Node.DIRECTORY:
            return obj.children.filter(is_deleted=False).count()
        return 0

    def _request_user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def get_is_owner(self, obj):
        user = self._request_user()
        return bool(user and obj.owner_id == user.id)

    def get_can_edit(self, obj):
        user = self._request_user()
        if not user:
            return False
        if obj.owner_id == user.id or user.is_admin_role or user.is_staff:
            return True
        return obj.permission_level == Node.PUBLIC

    def validate(self, attrs):
        node_type = attrs.get("node_type", getattr(self.instance, "node_type", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        if parent and parent.node_type != Node.DIRECTORY:
            raise serializers.ValidationError("Parent must be a directory.")
        if node_type == Node.DIRECTORY and attrs.get("content"):
            raise serializers.ValidationError("Directories cannot have content.")
        return attrs
