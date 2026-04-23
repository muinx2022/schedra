from rest_framework import serializers

from social.adapters import interaction_capabilities_for_account

from .models import InteractionMessage, InteractionThread


class InboxSyncRequestSerializer(serializers.Serializer):
    account = serializers.UUIDField(required=False)


class InteractionMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionMessage
        fields = [
            "id",
            "external_id",
            "parent_external_id",
            "parent_message",
            "author_name",
            "author_external_id",
            "body_text",
            "direction",
            "published_at",
            "metadata",
        ]


class InteractionThreadListSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(source="social_account_id", read_only=True)
    account_name = serializers.CharField(source="social_account.display_name", read_only=True)
    platform = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)
    related_post_id = serializers.UUIDField(source="post_target.post_id", allow_null=True, read_only=True)
    interaction_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = InteractionThread
        fields = [
            "id",
            "account_id",
            "account_name",
            "platform",
            "triage_status",
            "message_count",
            "last_message_at",
            "external_object_id",
            "related_post_id",
            "interaction_capabilities",
        ]

    def get_platform(self, obj):
        return obj.social_account.metadata.get("channel_code") or obj.social_account.provider.code

    def get_interaction_capabilities(self, obj):
        return interaction_capabilities_for_account(
            provider_code=obj.social_account.provider.code,
            account_type=obj.social_account.account_type,
        )


class InteractionThreadDetailSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(source="social_account_id", read_only=True)
    account_name = serializers.CharField(source="social_account.display_name", read_only=True)
    platform = serializers.SerializerMethodField()
    related_post_id = serializers.UUIDField(source="post_target.post_id", allow_null=True, read_only=True)
    messages = InteractionMessageSerializer(many=True, read_only=True)
    interaction_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = InteractionThread
        fields = [
            "id",
            "account_id",
            "account_name",
            "platform",
            "triage_status",
            "last_message_at",
            "last_synced_at",
            "external_object_id",
            "related_post_id",
            "interaction_capabilities",
            "messages",
        ]

    def get_platform(self, obj):
        return obj.social_account.metadata.get("channel_code") or obj.social_account.provider.code

    def get_interaction_capabilities(self, obj):
        return interaction_capabilities_for_account(
            provider_code=obj.social_account.provider.code,
            account_type=obj.social_account.account_type,
        )


class InteractionThreadWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionThread
        fields = ["triage_status"]


class InteractionReplySerializer(serializers.Serializer):
    parent_message_id = serializers.UUIDField()
    body_text = serializers.CharField()

    def validate_body_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reply text cannot be empty.")
        return value.strip()
