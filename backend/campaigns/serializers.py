from rest_framework import serializers
from django.conf import settings
from urllib.parse import urljoin

from media_library.models import MediaAsset
from media_library.serializers import MediaAssetSerializer

from .models import Campaign, CampaignMediaItem, CampaignMediaType, CampaignSegment


class CampaignSegmentSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = CampaignSegment
        fields = [
            "id",
            "order_index",
            "raw_text",
            "caption_text",
            "start_seconds",
            "end_seconds",
            "duration_seconds",
            "status",
            "draft_post",
        ]

    def get_duration_seconds(self, obj):
        return max(0, obj.end_seconds - obj.start_seconds)


class CampaignMediaItemSerializer(serializers.ModelSerializer):
    media_asset = MediaAssetSerializer(read_only=True)

    class Meta:
        model = CampaignMediaItem
        fields = ["id", "order_index", "media_asset"]


class CampaignSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True, max_length=200)
    source_media_type = serializers.ChoiceField(choices=CampaignMediaType.choices, required=False)
    source_video = serializers.PrimaryKeyRelatedField(
        queryset=MediaAsset.objects.none(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    source_video_detail = MediaAssetSerializer(source="source_video", read_only=True)
    source_images = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=MediaAsset.objects.none()),
        write_only=True,
        required=False,
    )
    source_images_detail = CampaignMediaItemSerializer(source="media_items", many=True, read_only=True)
    source_file_url = serializers.SerializerMethodField()
    source_file_name = serializers.SerializerMethodField()
    segments = CampaignSegmentSerializer(many=True, read_only=True)
    draft_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "title",
            "source_file",
            "source_file_url",
            "source_file_name",
            "source_file_type",
            "source_text",
            "source_media_type",
            "source_video",
            "source_video_detail",
            "source_images",
            "source_images_detail",
            "status",
            "segment_count",
            "total_video_duration_seconds",
            "segments",
            "draft_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "source_file_type",
            "source_text",
            "status",
            "segment_count",
            "total_video_duration_seconds",
            "segments",
            "draft_count",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            workspace_assets = request.user.workspace.media_assets.all()
            self.fields["source_video"].queryset = workspace_assets.filter(content_type__startswith="video/")
            self.fields["source_images"].child.queryset = workspace_assets.filter(content_type__startswith="image/")

    def validate_source_video(self, value):
        if not (value.content_type or "").startswith("video/"):
            raise serializers.ValidationError("Campaign source video must be a video asset.")
        return value

    def validate_source_images(self, value):
        for asset in value:
            if not (asset.content_type or "").startswith("image/"):
                raise serializers.ValidationError("Campaign source images must all be image assets.")
        return value

    def validate(self, attrs):
        title = attrs.get("title", "")
        media_type = attrs.get("source_media_type", CampaignMediaType.NONE)
        source_video = attrs.get("source_video")
        source_images = attrs.get("source_images", [])

        if not title.strip():
            raise serializers.ValidationError({"title": "Campaign title is required."})
        if media_type == CampaignMediaType.VIDEO and not source_video:
            raise serializers.ValidationError({"source_video": "Video media type requires a source video."})
        if media_type == CampaignMediaType.IMAGES and not source_images:
            raise serializers.ValidationError({"source_images": "Image media type requires at least one image."})
        if media_type != CampaignMediaType.VIDEO and source_video:
            raise serializers.ValidationError({"source_video": "Source video is only valid when media type is video."})
        if media_type != CampaignMediaType.IMAGES and source_images:
            raise serializers.ValidationError({"source_images": "Source images are only valid when media type is images."})
        return attrs

    def get_source_file_url(self, obj):
        if not obj.source_file:
            return ""
        public_base = (settings.APP_PUBLIC_BASE_URL or "").strip()
        if public_base:
            return urljoin(f"{public_base.rstrip('/')}/", obj.source_file.url.lstrip("/"))
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.source_file.url)
        return obj.source_file.url

    def get_source_file_name(self, obj):
        return obj.source_file.name.rsplit("/", 1)[-1] if obj.source_file else ""

    def get_draft_count(self, obj):
        return obj.segments.exclude(draft_post__isnull=True).count()
