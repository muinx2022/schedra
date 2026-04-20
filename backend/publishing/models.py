from django.conf import settings
from django.db import models

from accounts.models import Workspace
from common.models import BaseModel
from ideas.models import Idea
from media_library.models import MediaAsset
from social.models import SocialAccount


class EditorialState(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"
    ARCHIVED = "archived", "Archived"


class DeliveryStrategy(models.TextChoices):
    NOW = "now", "Publish now"
    QUEUE = "queue", "Queue"
    SCHEDULE = "schedule", "Schedule"


class DeliveryStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    QUEUED = "queued", "Queued"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHING = "publishing", "Publishing"
    PUBLISHED = "published", "Published"
    FAILED = "failed", "Failed"
    CANCELED = "canceled", "Canceled"


class ContentType(models.TextChoices):
    FEED_POST = "feed_post", "Feed post"


class Post(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    source_idea = models.ForeignKey(Idea, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    internal_name = models.CharField(max_length=200, blank=True)
    caption_text = models.TextField(blank=True)
    content_type = models.CharField(max_length=32, choices=ContentType.choices, default=ContentType.FEED_POST)
    editorial_state = models.CharField(max_length=32, choices=EditorialState.choices, default=EditorialState.DRAFT)
    delivery_strategy = models.CharField(max_length=32, choices=DeliveryStrategy.choices, default=DeliveryStrategy.NOW)
    delivery_status = models.CharField(max_length=32, choices=DeliveryStatus.choices, default=DeliveryStatus.DRAFT)
    payload = models.JSONField(default=dict, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)


class PostMedia(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media_items")
    media_asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="post_items")
    kind = models.CharField(max_length=32, default="image")
    role = models.CharField(max_length=32, default="primary")
    order_index = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order_index", "created_at"]


class PostTarget(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="targets")
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="post_targets")
    delivery_strategy = models.CharField(max_length=32, choices=DeliveryStrategy.choices)
    delivery_status = models.CharField(max_length=32, choices=DeliveryStatus.choices, default=DeliveryStatus.DRAFT)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    provider_payload_override = models.JSONField(default=dict, blank=True)
    provider_result = models.JSONField(default=dict, blank=True)


class PublishAttempt(BaseModel):
    post_target = models.ForeignKey(PostTarget, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=32, choices=DeliveryStatus.choices, default=DeliveryStatus.PUBLISHING)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_detail = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

