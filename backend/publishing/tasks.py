from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from config.celery import app
from social.adapters import get_provider_adapter

from .models import DeliveryStatus, PostTarget, PublishAttempt


def get_next_queue_slot_datetime(queue_slots, *, timezone_name: str, now: datetime | None = None) -> datetime:
    if not queue_slots:
        raise ValueError("No active queue slots.")

    tz = ZoneInfo(timezone_name or "UTC")
    current = (now or timezone.now()).astimezone(tz)
    ordered_slots = sorted(queue_slots, key=lambda slot: (slot.weekday, slot.local_time, slot.position))

    for offset in range(8):
        candidate_date = current.date() + timedelta(days=offset)
        weekday = candidate_date.weekday()
        day_slots = [slot for slot in ordered_slots if slot.weekday == weekday]
        if not day_slots:
            continue

        for slot in day_slots:
            scheduled = datetime.combine(candidate_date, slot.local_time, tzinfo=tz)
            if scheduled > current:
                return scheduled

    raise ValueError("No future queue slot found.")


@app.task
def dispatch_due_post_targets():
    now = timezone.now()
    due_targets = list(
        PostTarget.objects.select_related("post")
        .filter(
            Q(delivery_status=DeliveryStatus.SCHEDULED) | Q(delivery_status=DeliveryStatus.QUEUED),
            scheduled_at__isnull=False,
            scheduled_at__lte=now,
        )
        .order_by("scheduled_at", "created_at")
    )

    dispatched_target_ids: list[str] = []
    for target in due_targets:
        if target.delivery_status == DeliveryStatus.PUBLISHING:
            continue
        target.delivery_status = DeliveryStatus.PUBLISHING
        target.save(update_fields=["delivery_status", "updated_at"])
        target.post.delivery_status = DeliveryStatus.PUBLISHING
        target.post.save(update_fields=["delivery_status", "updated_at"])
        publish_post_target.delay(str(target.id))
        dispatched_target_ids.append(str(target.id))

    return {"dispatched_target_ids": dispatched_target_ids, "count": len(dispatched_target_ids)}


@app.task
def publish_post_target(post_target_id: str):
    post_target = PostTarget.objects.select_related("post", "social_account__provider").prefetch_related("post__media_items__media_asset").get(pk=post_target_id)
    adapter = get_provider_adapter(post_target.social_account.provider.code)
    request_payload = {
        "caption_text": post_target.post.caption_text,
        "payload": post_target.post.payload,
        "media_items": [
            {
                "id": str(item.media_asset_id),
                "kind": item.kind,
                "role": item.role,
                "order_index": item.order_index,
                "file_url": item.media_asset.get_public_file_url(),
            }
            for item in post_target.post.media_items.all().order_by("order_index", "created_at")
        ],
    }
    attempt = PublishAttempt.objects.create(
        post_target=post_target,
        status=DeliveryStatus.PUBLISHING,
        request_payload=request_payload,
    )
    try:
        response = adapter.publish_post(
            {
                "external_id": post_target.social_account.external_id,
                "display_name": post_target.social_account.display_name,
                "account_type": post_target.social_account.account_type,
                "access_token": post_target.social_account.metadata.get("access_token", ""),
                "refresh_token": post_target.social_account.metadata.get("refresh_token", ""),
                "page_access_token": post_target.social_account.metadata.get("page_access_token", ""),
                "parent_page_id": post_target.social_account.metadata.get("parent_page_id", ""),
                "username": post_target.social_account.metadata.get("username", ""),
            },
            request_payload,
        )
        attempt.status = DeliveryStatus.PUBLISHED
        attempt.response_payload = response
        attempt.finished_at = timezone.now()
        attempt.save()
        post_target.delivery_status = DeliveryStatus.PUBLISHED
        post_target.provider_result = response
        post_target.post.delivery_status = DeliveryStatus.PUBLISHED
        post_target.post.published_at = timezone.now()
        post_target.post.save(update_fields=["delivery_status", "published_at", "updated_at"])
        post_target.save(update_fields=["delivery_status", "provider_result", "updated_at"])
    except Exception as exc:
        attempt.status = DeliveryStatus.FAILED
        attempt.error_detail = str(exc)
        attempt.finished_at = timezone.now()
        attempt.save()
        post_target.delivery_status = DeliveryStatus.FAILED
        post_target.provider_result = {"error": str(exc)}
        post_target.post.delivery_status = DeliveryStatus.FAILED
        post_target.post.save(update_fields=["delivery_status", "updated_at"])
        post_target.save(update_fields=["delivery_status", "provider_result", "updated_at"])
