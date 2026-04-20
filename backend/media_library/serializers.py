from rest_framework import serializers

from .models import MediaAsset


class MediaAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    kind = serializers.CharField(read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "title",
            "file_url",
            "file_name",
            "kind",
            "content_type",
            "size_bytes",
            "storage_backend",
            "alt_text",
            "created_at",
        ]
        read_only_fields = ["file_name", "content_type", "size_bytes", "storage_backend", "created_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        return obj.get_file_url(request)
