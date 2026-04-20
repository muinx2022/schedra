from django.db import models

from common.models import BaseModel
from social.models import SocialAccount


class ProviderSyncType(models.TextChoices):
    INSIGHTS = "insights", "Insights"
    COMMENTS = "comments", "Comments"


class ProviderSyncStatus(models.TextChoices):
    IDLE = "idle", "Idle"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    ERROR = "error", "Error"


class ProviderSyncState(BaseModel):
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="provider_sync_states")
    sync_type = models.CharField(max_length=32, choices=ProviderSyncType.choices)
    status = models.CharField(max_length=32, choices=ProviderSyncStatus.choices, default=ProviderSyncStatus.IDLE)
    last_error = models.TextField(blank=True)
    cursor_or_checkpoint = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["social_account", "sync_type"], name="uniq_provider_sync_state")
        ]


class ProviderMetricKey(models.TextChoices):
    IMPRESSIONS = "impressions", "Impressions"
    REACH = "reach", "Reach"
    ENGAGEMENT = "engagement", "Engagement"


class ProviderDailyInsight(BaseModel):
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="provider_daily_insights")
    metric_date = models.DateField()
    metric_key = models.CharField(max_length=32, choices=ProviderMetricKey.choices)
    value = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "metric_date", "metric_key"],
                name="uniq_provider_daily_insight",
            )
        ]

