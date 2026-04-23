from rest_framework import serializers

from .adapters import interaction_capabilities_for_account
from .models import QueueSlot, SocialAccount, SocialConnection, SocialProvider


class SocialProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialProvider
        fields = ["id", "code", "name", "capabilities"]


class SocialConnectionSerializer(serializers.ModelSerializer):
    provider = SocialProviderSerializer(read_only=True)

    class Meta:
        model = SocialConnection
        fields = [
            "id",
            "provider",
            "external_user_id",
            "status",
            "expires_at",
            "scopes",
            "metadata",
            "created_at",
            "updated_at",
        ]


class QueueSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueSlot
        fields = ["id", "weekday", "local_time", "is_active", "position"]


class QueueSlotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueSlot
        fields = ["weekday", "local_time", "is_active", "position"]

    def validate_weekday(self, value):
        if value < 0 or value > 6:
            raise serializers.ValidationError("Weekday must be between 0 and 6.")
        return value


class SocialAccountSerializer(serializers.ModelSerializer):
    queue_slots = QueueSlotSerializer(many=True, read_only=True)
    provider_code = serializers.CharField(source="provider.code", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    channel_code = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    interaction_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = SocialAccount
        fields = [
            "id",
            "connection",
            "provider",
            "provider_code",
            "provider_name",
            "channel_code",
            "channel_name",
            "account_type",
            "external_id",
            "display_name",
            "status",
            "timezone",
            "metadata",
            "interaction_capabilities",
            "queue_slots",
            "created_at",
        ]
        read_only_fields = ["provider", "created_at"]

    def get_channel_code(self, obj):
        if obj.provider.code == "meta":
            if obj.account_type == "instagram_business":
                return "instagram"
            return "facebook"
        return obj.provider.code

    def get_channel_name(self, obj):
        if obj.provider.code == "meta":
            if obj.account_type == "instagram_business":
                return "Instagram"
            if obj.account_type == "page":
                return "Facebook"
        return obj.provider.name

    def get_interaction_capabilities(self, obj):
        return interaction_capabilities_for_account(
            provider_code=obj.provider.code,
            account_type=obj.account_type,
        )


class OAuthStartSerializer(serializers.Serializer):
    redirect_uri = serializers.URLField()


class OAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    redirect_uri = serializers.URLField()


class ConnectAccountSerializer(serializers.Serializer):
    external_id = serializers.CharField()
