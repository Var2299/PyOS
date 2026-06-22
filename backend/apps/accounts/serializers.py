from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_admin_role",
            "is_staff",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "is_staff"]


class AdminUserSerializer(serializers.ModelSerializer):
    """User record enriched with workspace usage stats for the admin panel."""

    files_created = serializers.IntegerField(read_only=True)
    directories_created = serializers.IntegerField(read_only=True)
    space_used = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_admin_role",
            "is_staff",
            "is_active",
            "created_at",
            "files_created",
            "directories_created",
            "space_used",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "is_admin_role"]
        read_only_fields = ["is_admin_role"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # The very first account created becomes the system administrator.
        # Every subsequent registration is a normal user.
        if not User.objects.exists():
            user.is_admin_role = True
            user.is_staff = True
            user.is_superuser = True
        user.save()
        # Give the new user a home directory (/home/<username>), like the CLI.
        from apps.filesystem.scaffolding import create_home_for
        create_home_for(user)
        return user
