from django.db import transaction

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ideas.models import Idea
from media_library.cleanup import delete_media_assets_if_unreferenced
from social.models import QueueSlot

from .models import DeliveryStatus, Post
from .serializers import PostSerializer
from .tasks import get_next_queue_slot_datetime, publish_post_target


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(workspace=self.request.user.workspace).prefetch_related("media_items", "targets").order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.user.workspace, author=self.request.user)

    def perform_destroy(self, instance):
        media_assets = [item.media_asset for item in instance.media_items.select_related("media_asset")]
        post_id = instance.id
        with transaction.atomic():
            instance.delete()
        delete_media_assets_if_unreferenced(media_assets, ignored_post_ids=[post_id])

    @action(detail=False, methods=["post"], url_path="from-idea/(?P<idea_id>[^/.]+)")
    def from_idea(self, request, idea_id=None):
        idea = Idea.objects.get(pk=idea_id, workspace=request.user.workspace)
        post = Post.objects.create(
            workspace=request.user.workspace,
            author=request.user,
            source_idea=idea,
            internal_name=idea.title,
            caption_text=idea.note,
            payload={"version": 1, "feed_post": {}},
        )
        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def publish_now(self, request, pk=None):
        post = self.get_object()
        targets = list(post.targets.all())
        if not targets:
            return Response({"detail": "Post needs a target account."}, status=status.HTTP_400_BAD_REQUEST)
        post.delivery_status = DeliveryStatus.PUBLISHING
        post.save(update_fields=["delivery_status", "updated_at"])
        target_ids = []
        for target in targets:
            target.delivery_status = DeliveryStatus.PUBLISHING
            target.save(update_fields=["delivery_status", "updated_at"])
            publish_post_target.delay(str(target.id))
        post.refresh_from_db()
        return Response(PostSerializer(post).data)

    @action(detail=True, methods=["post"])
    def queue(self, request, pk=None):
        post = self.get_object()
        target = post.targets.first()
        if not target:
            return Response({"detail": "Post needs a target account."}, status=status.HTTP_400_BAD_REQUEST)
        slots = list(
            QueueSlot.objects.filter(social_account=target.social_account, is_active=True).order_by(
                "weekday", "local_time", "position"
            )
        )
        if not slots:
            return Response({"detail": "No active queue slots."}, status=status.HTTP_400_BAD_REQUEST)
        scheduled_at = get_next_queue_slot_datetime(
            slots,
            timezone_name=target.social_account.timezone or request.user.workspace.timezone,
        )
        post.delivery_status = DeliveryStatus.QUEUED
        target.delivery_status = DeliveryStatus.QUEUED
        post.delivery_strategy = "queue"
        target.delivery_strategy = "queue"
        post.scheduled_at = scheduled_at
        target.scheduled_at = scheduled_at
        post.save(update_fields=["delivery_status", "delivery_strategy", "scheduled_at", "updated_at"])
        target.save(update_fields=["delivery_status", "delivery_strategy", "scheduled_at", "updated_at"])
        return Response(
            {
                "slot": {
                    "weekday": scheduled_at.weekday(),
                    "local_time": scheduled_at.strftime("%H:%M:%S"),
                    "scheduled_at": scheduled_at,
                },
                "post": PostSerializer(post).data,
            }
        )

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        post = self.get_object()
        target = post.targets.first()
        scheduled_at = request.data.get("scheduled_at")
        if not target or not scheduled_at:
            return Response({"detail": "Post target and scheduled_at are required."}, status=status.HTTP_400_BAD_REQUEST)
        post.delivery_strategy = "schedule"
        post.delivery_status = DeliveryStatus.SCHEDULED
        target.delivery_strategy = "schedule"
        target.delivery_status = DeliveryStatus.SCHEDULED
        post.scheduled_at = scheduled_at
        target.scheduled_at = scheduled_at
        post.save(update_fields=["delivery_strategy", "delivery_status", "scheduled_at", "updated_at"])
        target.save(update_fields=["delivery_strategy", "delivery_status", "scheduled_at", "updated_at"])
        return Response(PostSerializer(post).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        post = self.get_object()
        targets = list(post.targets.all())
        if not targets:
            return Response({"detail": "Post needs a target account."}, status=status.HTTP_400_BAD_REQUEST)
        for target in targets:
            publish_post_target.delay(str(target.id))
        return Response({"status": "queued_for_retry", "post_id": str(post.id)})
