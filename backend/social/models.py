from django.db import models

from accounts.models import Workspace
from common.models import BaseModel


class SocialProviderCode(models.TextChoices):
    FACEBOOK = "facebook", "Facebook"
    INSTAGRAM = "instagram", "Instagram"
    META = "meta", "Meta"
    LINKEDIN = "linkedin", "LinkedIn"
    TIKTOK = "tiktok", "TikTok"
    YOUTUBE = "youtube", "YouTube"
    PINTEREST = "pinterest", "Pinterest"


class ConnectionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONNECTED = "connected", "Connected"
    REAUTH_REQUIRED = "reauth_required", "Reauth required"


class SocialProvider(BaseModel):
    code = models.CharField(max_length=32, choices=SocialProviderCode.choices, unique=True)
    name = models.CharField(max_length=100)
    capabilities = models.JSONField(default=dict, blank=True)


class SocialConnection(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="social_connections")
    provider = models.ForeignKey(SocialProvider, on_delete=models.CASCADE, related_name="connections")
    external_user_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=ConnectionStatus.choices, default=ConnectionStatus.PENDING)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("workspace", "provider")]


class SocialAccount(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="social_accounts")
    connection = models.ForeignKey(SocialConnection, on_delete=models.CASCADE, related_name="accounts")
    provider = models.ForeignKey(SocialProvider, on_delete=models.CASCADE, related_name="accounts")
    account_type = models.CharField(max_length=32, default="page")
    external_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, default="active")
    timezone = models.CharField(max_length=64, default="Asia/Saigon")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("provider", "external_id", "workspace")]


class QueueSlot(BaseModel):
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="queue_slots")
    weekday = models.PositiveSmallIntegerField()
    local_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["weekday", "local_time", "position"]
