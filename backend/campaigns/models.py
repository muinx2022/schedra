from django.conf import settings
from django.db import models

from accounts.models import Workspace
from common.models import BaseModel
from media_library.models import MediaAsset
from publishing.models import Post


class CampaignStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    GENERATED = "generated", "Generated"
    DRAFTED = "drafted", "Drafted"
    FAILED = "failed", "Failed"


class CampaignSegmentStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    DRAFTED = "drafted", "Drafted"


class CampaignMediaType(models.TextChoices):
    NONE = "none", "No media"
    VIDEO = "video", "Video"
    IMAGES = "images", "Images"


class Campaign(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="campaigns")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaigns")
    title = models.CharField(max_length=200)
    source_file = models.FileField(upload_to="campaign_sources/")
    source_file_type = models.CharField(max_length=16)
    source_text = models.TextField(blank=True)
    source_media_type = models.CharField(
        max_length=16,
        choices=CampaignMediaType.choices,
        default=CampaignMediaType.NONE,
    )
    source_video = models.ForeignKey(
        MediaAsset,
        on_delete=models.PROTECT,
        related_name="campaigns",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=16, choices=CampaignStatus.choices, default=CampaignStatus.UPLOADED)
    segment_count = models.PositiveIntegerField(default=0)
    total_video_duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-updated_at", "-created_at"]


class CampaignSegment(BaseModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="segments")
    order_index = models.PositiveIntegerField()
    raw_text = models.TextField()
    caption_text = models.TextField()
    start_seconds = models.PositiveIntegerField(default=0)
    end_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=CampaignSegmentStatus.choices,
        default=CampaignSegmentStatus.GENERATED,
    )
    draft_post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_segments",
    )

    class Meta:
        ordering = ["order_index", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "order_index"], name="campaign_segment_unique_order"),
        ]


class CampaignMediaItem(BaseModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="media_items")
    media_asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="campaign_items")
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order_index", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "media_asset"], name="campaign_media_unique_asset"),
            models.UniqueConstraint(fields=["campaign", "order_index"], name="campaign_media_unique_order"),
        ]
