from rest_framework import serializers

from social.adapters import interaction_capabilities_for_account

from .models import InteractionMessage, InteractionThread


class InboxSyncRequestSerializer(serializers.Serializer):
    account = serializers.UUIDField(required=False)


class CommunityPostListItemSerializer(serializers.Serializer):
    external_object_id = serializers.CharField()
    thread_id = serializers.UUIDField(allow_null=True)
    related_post_id = serializers.UUIDField(allow_null=True)
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    platform = serializers.CharField()
    title = serializers.CharField()
    body_text = serializers.CharField(allow_blank=True)
    snippet = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    last_activity_at = serializers.DateTimeField(allow_null=True)
    permalink_url = serializers.CharField(allow_blank=True)
    preview_image_url = serializers.CharField(allow_blank=True)
    comment_count = serializers.IntegerField()
    triage_status = serializers.CharField()
    interaction_capabilities = serializers.DictField()


class CommunityPostMessageSerializer(serializers.Serializer):
    id = serializers.CharField()
    external_id = serializers.CharField()
    parent_external_id = serializers.CharField(allow_blank=True)
    author_name = serializers.CharField()
    author_external_id = serializers.CharField(allow_blank=True)
    body_text = serializers.CharField(allow_blank=True)
    direction = serializers.CharField()
    published_at = serializers.DateTimeField()
    metadata = serializers.DictField()


class CommunityPostDetailSerializer(serializers.Serializer):
    external_object_id = serializers.CharField()
    thread_id = serializers.UUIDField(allow_null=True)
    related_post_id = serializers.UUIDField(allow_null=True)
    account_id = serializers.UUIDField()
    account_name = serializers.CharField()
    platform = serializers.CharField()
    title = serializers.CharField()
    body_text = serializers.CharField(allow_blank=True)
    published_at = serializers.DateTimeField(allow_null=True)
    last_activity_at = serializers.DateTimeField(allow_null=True)
    permalink_url = serializers.CharField(allow_blank=True)
    preview_image_url = serializers.CharField(allow_blank=True)
    comment_count = serializers.IntegerField()
    triage_status = serializers.CharField()
    interaction_capabilities = serializers.DictField()
    messages = CommunityPostMessageSerializer(many=True)


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
    post_label = serializers.SerializerMethodField()
    latest_message_preview = serializers.SerializerMethodField()
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
            "post_label",
            "latest_message_preview",
            "interaction_capabilities",
        ]

    def get_platform(self, obj):
        return obj.social_account.metadata.get("channel_code") or obj.social_account.provider.code

    def get_interaction_capabilities(self, obj):
        return interaction_capabilities_for_account(
            provider_code=obj.social_account.provider.code,
            account_type=obj.social_account.account_type,
        )

    def get_post_label(self, obj):
        post = getattr(obj.post_target, "post", None)
        if not post:
            return ""
        return (post.internal_name or post.caption_text or "").strip()

    def get_latest_message_preview(self, obj):
        latest_message = obj.messages.order_by("-published_at", "-created_at").first()
        if not latest_message:
            return ""
        return (latest_message.body_text or "").strip()


class InteractionThreadDetailSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(source="social_account_id", read_only=True)
    account_name = serializers.CharField(source="social_account.display_name", read_only=True)
    platform = serializers.SerializerMethodField()
    related_post_id = serializers.UUIDField(source="post_target.post_id", allow_null=True, read_only=True)
    post_label = serializers.SerializerMethodField()
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
            "post_label",
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

    def get_post_label(self, obj):
        post = getattr(obj.post_target, "post", None)
        if not post:
            return ""
        return (post.internal_name or post.caption_text or "").strip()


class InteractionThreadWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionThread
        fields = ["triage_status"]


class InteractionReplySerializer(serializers.Serializer):
    parent_message_id = serializers.CharField()
    body_text = serializers.CharField()

    def validate_parent_message_id(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reply target is required.")
        return value.strip()

    def validate_body_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reply text cannot be empty.")
        return value.strip()


class InteractionPostCommentSerializer(serializers.Serializer):
    body_text = serializers.CharField()

    def validate_body_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        return value.strip()
