from django.db import transaction
from django.core.files.storage import default_storage
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from media_library.cleanup import delete_media_assets_if_unreferenced
from publishing.models import DeliveryStatus, EditorialState, Post, PostMedia

from .models import (
    Campaign,
    CampaignMediaItem,
    CampaignMediaType,
    CampaignSegment,
    CampaignSegmentStatus,
    CampaignStatus,
)
from .serializers import CampaignSerializer
from .services import (
    CampaignProcessingError,
    build_segment_ranges,
    extract_text_from_source_file,
    get_source_file_type,
    get_video_duration_seconds,
    parse_segments,
)


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Campaign.objects.filter(workspace=self.request.user.workspace)
            .select_related("source_video")
            .prefetch_related("segments", "media_items__media_asset")
            .order_by("-updated_at")
        )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if hasattr(request.data, "getlist"):
            source_images = request.data.getlist("source_images")
            if source_images:
                data.setlist("source_images", source_images)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        source_file = serializer.validated_data["source_file"]
        try:
            source_file_type = get_source_file_type(source_file.name)
        except CampaignProcessingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        title = serializer.validated_data["title"]
        source_images = serializer.validated_data.get("source_images", [])
        with transaction.atomic():
            campaign = Campaign.objects.create(
                workspace=request.user.workspace,
                author=request.user,
                title=title,
                source_file=source_file,
                source_file_type=source_file_type,
                source_media_type=serializer.validated_data.get("source_media_type", CampaignMediaType.NONE),
                source_video=serializer.validated_data.get("source_video"),
                status=CampaignStatus.UPLOADED,
            )
            for index, asset in enumerate(source_images):
                CampaignMediaItem.objects.create(campaign=campaign, media_asset=asset, order_index=index)
        response_serializer = self.get_serializer(campaign)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        campaign_id = instance.id
        source_file_name = instance.source_file.name if instance.source_file else ""
        media_assets = []
        if instance.source_video_id:
            media_assets.append(instance.source_video)
        media_assets.extend(item.media_asset for item in instance.media_items.select_related("media_asset"))

        with transaction.atomic():
            instance.delete()

        if source_file_name and default_storage.exists(source_file_name):
            default_storage.delete(source_file_name)
        delete_media_assets_if_unreferenced(media_assets, ignored_campaign_ids=[campaign_id])

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        campaign = self.get_object()
        if campaign.segments.filter(draft_post__isnull=False).exists():
            return Response(
                {"detail": "This campaign already has drafts. Create a new campaign to regenerate segments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            source_text = extract_text_from_source_file(campaign.source_file)
            segment_texts = parse_segments(source_text)
            total_duration_seconds = 0
            if campaign.source_media_type == CampaignMediaType.VIDEO:
                total_duration_seconds = get_video_duration_seconds(campaign.source_video)
                ranges = build_segment_ranges(total_duration_seconds, len(segment_texts))
            else:
                ranges = [(0, 0) for _ in segment_texts]
        except CampaignProcessingError as exc:
            campaign.status = CampaignStatus.FAILED
            campaign.save(update_fields=["status", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            campaign.segments.all().delete()
            segments = []
            for index, (raw_text, range_pair) in enumerate(zip(segment_texts, ranges)):
                start_seconds, end_seconds = range_pair
                segments.append(
                    CampaignSegment(
                        campaign=campaign,
                        order_index=index,
                        raw_text=raw_text,
                        caption_text=raw_text,
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        status=CampaignSegmentStatus.GENERATED,
                    )
                )
            CampaignSegment.objects.bulk_create(segments)
            campaign.source_text = source_text
            campaign.segment_count = len(segment_texts)
            campaign.total_video_duration_seconds = total_duration_seconds
            campaign.status = CampaignStatus.GENERATED
            campaign.save(
                update_fields=[
                    "source_text",
                    "segment_count",
                    "total_video_duration_seconds",
                    "status",
                    "updated_at",
                ]
            )

        campaign.refresh_from_db()
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=["post"], url_path="create-drafts")
    def create_drafts(self, request, pk=None):
        campaign = self.get_object()
        segments = list(campaign.segments.select_related("draft_post").order_by("order_index"))
        if not segments:
            return Response({"detail": "Generate segments before creating drafts."}, status=status.HTTP_400_BAD_REQUEST)
        media_items = list(campaign.media_items.select_related("media_asset").order_by("order_index"))

        created_count = 0
        with transaction.atomic():
            for segment in segments:
                if segment.draft_post_id:
                    continue
                post = Post.objects.create(
                    workspace=request.user.workspace,
                    author=request.user,
                    internal_name=f"{campaign.title} - Segment {segment.order_index + 1}",
                    caption_text=segment.raw_text,
                    editorial_state=EditorialState.DRAFT,
                    delivery_status=DeliveryStatus.DRAFT,
                    delivery_strategy="now",
                    payload={
                        "version": 1,
                        "feed_post": {},
                        "campaign": {
                            "campaign_id": str(campaign.id),
                            "segment_id": str(segment.id),
                            "segment_index": segment.order_index,
                        },
                    },
                )
                if campaign.source_media_type == CampaignMediaType.VIDEO and campaign.source_video_id:
                    PostMedia.objects.create(
                        post=post,
                        media_asset=campaign.source_video,
                        kind="video",
                        role="primary",
                        order_index=0,
                        metadata={
                            "clip_start_seconds": segment.start_seconds,
                            "clip_end_seconds": segment.end_seconds,
                            "clip_duration_seconds": max(0, segment.end_seconds - segment.start_seconds),
                            "source_campaign_id": str(campaign.id),
                            "source_segment_id": str(segment.id),
                        },
                    )
                elif campaign.source_media_type == CampaignMediaType.IMAGES and segment.order_index < len(media_items):
                    image_item = media_items[segment.order_index]
                    PostMedia.objects.create(
                        post=post,
                        media_asset=image_item.media_asset,
                        kind="image",
                        role="primary",
                        order_index=0,
                        metadata={
                            "source_campaign_id": str(campaign.id),
                            "source_segment_id": str(segment.id),
                            "source_campaign_media_item_id": str(image_item.id),
                        },
                    )
                segment.draft_post = post
                segment.status = CampaignSegmentStatus.DRAFTED
                segment.save(update_fields=["draft_post", "status", "updated_at"])
                created_count += 1

            campaign.status = CampaignStatus.DRAFTED
            campaign.save(update_fields=["status", "updated_at"])

        campaign.refresh_from_db()
        return Response(
            {
                "created_count": created_count,
                "draft_count": campaign.segments.exclude(draft_post__isnull=True).count(),
                "campaign": self.get_serializer(campaign).data,
            }
        )
