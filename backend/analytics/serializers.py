from rest_framework import serializers


class AnalyticsQuerySerializer(serializers.Serializer):
    range = serializers.ChoiceField(choices=["7d", "30d", "90d"], default="30d", required=False)
    account = serializers.UUIDField(required=False)


class AnalyticsSyncRequestSerializer(serializers.Serializer):
    account = serializers.UUIDField(required=False)


class AnalyticsFiltersSerializer(serializers.Serializer):
    range = serializers.CharField()
    account_id = serializers.UUIDField(allow_null=True)
    workspace_timezone = serializers.CharField()


class AnalyticsSummarySerializer(serializers.Serializer):
    connected_channels = serializers.IntegerField()
    active_queue_slots = serializers.IntegerField()
    published_attempts = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()
    success_rate = serializers.IntegerField()


class AnalyticsSeriesPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    published_attempts = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()


class AnalyticsChannelSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    display_name = serializers.CharField()
    provider_code = serializers.CharField()
    channel_code = serializers.CharField()
    active_queue_slots = serializers.IntegerField()
    published_attempts = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()
    success_rate = serializers.IntegerField()
    last_activity_at = serializers.DateTimeField(allow_null=True)


class AnalyticsFailureSerializer(serializers.Serializer):
    post_id = serializers.UUIDField()
    post_target_id = serializers.UUIDField()
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    finished_at = serializers.DateTimeField()
    error_detail = serializers.CharField()


class ProviderSyncSerializer(serializers.Serializer):
    status = serializers.CharField()
    last_success_at = serializers.DateTimeField(allow_null=True)
    last_error = serializers.CharField(allow_blank=True)
    freshness_minutes = serializers.IntegerField(allow_null=True)


class ProviderSummarySerializer(serializers.Serializer):
    impressions = serializers.IntegerField()
    reach = serializers.IntegerField()
    engagement = serializers.IntegerField()


class ProviderSeriesPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    impressions = serializers.IntegerField()
    reach = serializers.IntegerField()
    engagement = serializers.IntegerField()


class ProviderChannelSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    display_name = serializers.CharField()
    channel_code = serializers.CharField()
    impressions = serializers.IntegerField()
    reach = serializers.IntegerField()
    engagement = serializers.IntegerField()
    synced_at = serializers.DateTimeField(allow_null=True)
    sync_status = serializers.CharField()


class WorkspaceAnalyticsSerializer(serializers.Serializer):
    source = serializers.CharField()
    generated_at = serializers.DateTimeField()
    filters = AnalyticsFiltersSerializer()
    summary = AnalyticsSummarySerializer()
    series = AnalyticsSeriesPointSerializer(many=True)
    channels = AnalyticsChannelSerializer(many=True)
    recent_failures = AnalyticsFailureSerializer(many=True)
    provider_sync = ProviderSyncSerializer()
    provider_summary = ProviderSummarySerializer()
    provider_series = ProviderSeriesPointSerializer(many=True)
    provider_channels = ProviderChannelSerializer(many=True)
