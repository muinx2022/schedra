from django.contrib.auth.models import User
from django.utils.text import slugify
from rest_framework import serializers

from .models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "timezone", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    workspace = WorkspaceSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "workspace"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=150)
    workspace_name = serializers.CharField(max_length=160)

    def create(self, validated_data):
        email = validated_data["email"].lower()
        full_name = validated_data["full_name"].strip()
        workspace_name = validated_data["workspace_name"].strip()
        base_username = slugify(email.split("@")[0]) or "user"
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}{suffix}"

        first_name, _, last_name = full_name.partition(" ")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
        )

        base_slug = slugify(workspace_name) or f"{username}-workspace"
        slug = base_slug
        index = 1
        while Workspace.objects.filter(slug=slug).exists():
            index += 1
            slug = f"{base_slug}-{index}"

        Workspace.objects.create(owner=user, name=workspace_name, slug=slug)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

