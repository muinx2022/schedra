from django.db import models

from accounts.models import Workspace
from common.models import BaseModel
from publishing.models import PostTarget
from social.models import SocialAccount


class InteractionThreadType(models.TextChoices):
    COMMENTS = "comments", "Comments"


class InteractionTriageStatus(models.TextChoices):
    NEW = "new", "New"
    REVIEWING = "reviewing", "Reviewing"
    RESOLVED = "resolved", "Resolved"
    IGNORED = "ignored", "Ignored"


class InteractionDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"


class InteractionThread(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="interaction_threads")
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="interaction_threads")
    post_target = models.ForeignKey(PostTarget, on_delete=models.SET_NULL, null=True, blank=True, related_name="interaction_threads")
    thread_type = models.CharField(max_length=32, choices=InteractionThreadType.choices, default=InteractionThreadType.COMMENTS)
    external_object_id = models.CharField(max_length=255)
    triage_status = models.CharField(max_length=32, choices=InteractionTriageStatus.choices, default=InteractionTriageStatus.NEW)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_cursor = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "thread_type", "external_object_id"],
                name="uniq_interaction_thread_object",
            )
        ]


class InteractionMessage(BaseModel):
    thread = models.ForeignKey(InteractionThread, on_delete=models.CASCADE, related_name="messages")
    parent_message = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    external_id = models.CharField(max_length=255)
    parent_external_id = models.CharField(max_length=255, blank=True)
    author_name = models.CharField(max_length=255)
    author_external_id = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    direction = models.CharField(max_length=32, choices=InteractionDirection.choices, default=InteractionDirection.INBOUND)
    published_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["published_at", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["thread", "external_id"], name="uniq_interaction_message_external"),
        ]

