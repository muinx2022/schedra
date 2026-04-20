from rest_framework import serializers

from media_library.models import MediaAsset
from social.models import SocialAccount
from .models import Post, PostMedia, PostTarget


class PostMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PostMedia
        fields = ["id", "media_asset", "file_url", "kind", "role", "order_index", "metadata"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        try:
            return obj.media_asset.get_file_url(request)
        except Exception:
            return None


class PostTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTarget
        fields = [
            "id",
            "social_account",
            "delivery_strategy",
            "delivery_status",
            "scheduled_at",
            "provider_payload_override",
            "provider_result",
        ]
        read_only_fields = ["delivery_status", "provider_result"]


class PostSerializer(serializers.ModelSerializer):
    media_items = PostMediaSerializer(many=True, required=False)
    targets = PostTargetSerializer(many=True, required=False)

    class Meta:
        model = Post
        fields = [
            "id",
            "workspace",
            "author",
            "source_idea",
            "internal_name",
            "caption_text",
            "content_type",
            "editorial_state",
            "delivery_strategy",
            "delivery_status",
            "payload",
            "scheduled_at",
            "published_at",
            "media_items",
            "targets",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["workspace", "author", "published_at", "created_at", "updated_at"]

    def validate(self, attrs):
        targets = attrs.get("targets")
        media_items = attrs.get("media_items")
        payload = attrs.get("payload")

        instance = getattr(self, "instance", None)
        if targets is None and instance is not None:
            targets = list(instance.targets.all().values("social_account"))
        if media_items is None and instance is not None:
            media_items = list(instance.media_items.all().values("media_asset", "kind", "role", "order_index", "metadata"))
        if payload is None and instance is not None:
            payload = instance.payload

        if not targets:
            return attrs
        if len(targets) > 1:
            raise serializers.ValidationError("Only one target account is supported per post in v1.")

        social_account_value = targets[0]["social_account"]
        social_account_id = getattr(social_account_value, "id", social_account_value)
        account = SocialAccount.objects.filter(pk=social_account_id).first()
        if not account:
            return attrs

        feed_payload = (payload or {}).get("feed_post") or {}
        mode = feed_payload.get("mode") or "single"
        media_count = len(media_items or [])

        if account.account_type == "instagram_business":
            if media_count < 1:
                raise serializers.ValidationError("Instagram posts require at least one image.")
            if mode == "carousel":
                if media_count < 2:
                    raise serializers.ValidationError("Instagram carousel posts require at least two images.")
            elif media_count != 1:
                raise serializers.ValidationError("Instagram single posts require exactly one image.")
        return attrs

    @staticmethod
    def _resolve_media_kind(item: dict) -> dict:
        """Auto-derive kind from MediaAsset.content_type if not explicitly set to 'video'."""
        asset = item.get("media_asset")
        if asset and item.get("kind", "image") == "image":
            ct = getattr(asset, "content_type", "") or ""
            if ct.startswith("video/"):
                return {**item, "kind": "video"}
        return item

    def create(self, validated_data):
        media_items = validated_data.pop("media_items", [])
        targets = validated_data.pop("targets", [])
        post = Post.objects.create(**validated_data)
        for item in media_items:
            item = self._resolve_media_kind(item)
            PostMedia.objects.create(post=post, **item)
        for item in targets:
            PostTarget.objects.create(post=post, **item)
        return post

    def update(self, instance, validated_data):
        media_items = validated_data.pop("media_items", None)
        targets = validated_data.pop("targets", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if media_items is not None:
            instance.media_items.all().delete()
            for item in media_items:
                item = self._resolve_media_kind(item)
                PostMedia.objects.create(post=instance, **item)
        if targets is not None:
            instance.targets.all().delete()
            for item in targets:
                PostTarget.objects.create(post=instance, **item)
        return instance
