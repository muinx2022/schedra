from rest_framework import serializers

from .models import Idea


class IdeaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Idea
        fields = [
            "id",
            "workspace",
            "author",
            "title",
            "note",
            "column",
            "tags",
            "image_urls",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["workspace", "author", "created_at", "updated_at"]

