from __future__ import annotations

from collections.abc import Iterable

from django.db.models import QuerySet

from .models import MediaAsset
from .storage import get_backend_by_id


def delete_media_asset_file(asset: MediaAsset) -> None:
    storage_key = asset.storage_key or (asset.file.name if asset.file else "")
    if not storage_key:
        return
    get_backend_by_id(asset.storage_backend).delete(storage_key, content_type=asset.content_type)


def _normalize_ids(values: Iterable | None) -> set[str]:
    return {str(value) for value in (values or []) if value}


def _has_references_outside(
    asset: MediaAsset,
    ignored_post_ids: set[str],
    ignored_campaign_ids: set[str],
) -> bool:
    from campaigns.models import Campaign, CampaignMediaItem
    from publishing.models import PostMedia

    post_media: QuerySet = PostMedia.objects.filter(media_asset=asset)
    if ignored_post_ids:
        post_media = post_media.exclude(post_id__in=ignored_post_ids)
    for campaign_id in ignored_campaign_ids:
        post_media = post_media.exclude(metadata__source_campaign_id=campaign_id)
    if post_media.exists():
        return True

    campaign_items: QuerySet = CampaignMediaItem.objects.filter(media_asset=asset)
    if ignored_campaign_ids:
        campaign_items = campaign_items.exclude(campaign_id__in=ignored_campaign_ids)
    if campaign_items.exists():
        return True

    source_video_campaigns: QuerySet = Campaign.objects.filter(source_video=asset)
    if ignored_campaign_ids:
        source_video_campaigns = source_video_campaigns.exclude(id__in=ignored_campaign_ids)
    return source_video_campaigns.exists()


def delete_media_assets_if_unreferenced(
    media_assets: Iterable[MediaAsset],
    *,
    ignored_post_ids: Iterable | None = None,
    ignored_campaign_ids: Iterable | None = None,
) -> int:
    ignored_post_id_set = _normalize_ids(ignored_post_ids)
    ignored_campaign_id_set = _normalize_ids(ignored_campaign_ids)
    deleted_count = 0
    seen_ids: set[str] = set()

    for asset in media_assets:
        if not asset or str(asset.id) in seen_ids:
            continue
        seen_ids.add(str(asset.id))
        if _has_references_outside(asset, ignored_post_id_set, ignored_campaign_id_set):
            continue
        delete_media_asset_file(asset)
        asset.delete()
        deleted_count += 1

    return deleted_count
