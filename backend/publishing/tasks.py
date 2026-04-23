from datetime import datetime, timedelta
import time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from config.celery import app
from social.adapters import get_provider_adapter

from .models import DeliveryStatus, PostTarget, PublishAttempt


PUBLISH_STATUS_POLL_ATTEMPTS = 8
PUBLISH_STATUS_POLL_DELAY_SECONDS = 3


def _is_transient_publish_status_error(post_target: PostTarget, exc: Exception) -> bool:
    provider_code = (post_target.social_account.provider.code or "").lower()
    if provider_code != "tiktok":
        return False
    return "Could not reach TikTok API from the local backend." in str(exc)


def _sync_post_delivery_state(post) -> None:
    statuses = list(post.targets.values_list("delivery_status", flat=True))
    if not statuses:
        return

    next_status = post.delivery_status
    if any(status == DeliveryStatus.PUBLISHING for status in statuses):
        next_status = DeliveryStatus.PUBLISHING
    elif any(status == DeliveryStatus.QUEUED for status in statuses):
        next_status = DeliveryStatus.QUEUED
    elif any(status == DeliveryStatus.SCHEDULED for status in statuses):
        next_status = DeliveryStatus.SCHEDULED
    elif all(status == DeliveryStatus.PUBLISHED for status in statuses):
        next_status = DeliveryStatus.PUBLISHED
    elif any(status == DeliveryStatus.FAILED for status in statuses):
        next_status = DeliveryStatus.FAILED
    elif all(status == DeliveryStatus.CANCELED for status in statuses):
        next_status = DeliveryStatus.CANCELED
    elif all(status == DeliveryStatus.DRAFT for status in statuses):
        next_status = DeliveryStatus.DRAFT

    update_fields = ["updated_at"]
    if post.delivery_status != next_status:
        post.delivery_status = next_status
        update_fields.insert(0, "delivery_status")

    if next_status == DeliveryStatus.PUBLISHED and not post.published_at:
        post.published_at = timezone.now()
        update_fields.insert(0, "published_at")
    elif next_status != DeliveryStatus.PUBLISHED and post.published_at is not None:
        post.published_at = None
        update_fields.insert(0, "published_at")

    post.save(update_fields=update_fields)


def enqueue_publish_post_target(post_target: PostTarget) -> None:
    publish_post_target.delay(str(post_target.id))
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        post_target.refresh_from_db()
        has_attempt = PublishAttempt.objects.filter(post_target=post_target).exists()
        if has_attempt or post_target.delivery_status == DeliveryStatus.PUBLISHING:
            return
        post_target.delivery_status = DeliveryStatus.PUBLISHING
        post_target.save(update_fields=["delivery_status", "updated_at"])
        _sync_post_delivery_state(post_target.post)
        return
    post_target.delivery_status = DeliveryStatus.PUBLISHING
    post_target.save(update_fields=["delivery_status", "updated_at"])
    _sync_post_delivery_state(post_target.post)


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
    dispatch_errors: list[dict[str, str]] = []
    for target in due_targets:
        if target.delivery_status == DeliveryStatus.PUBLISHING:
            continue
        try:
            enqueue_publish_post_target(target)
            dispatched_target_ids.append(str(target.id))
        except Exception as exc:
            dispatch_errors.append({"target_id": str(target.id), "error": str(exc)})

    return {
        "dispatched_target_ids": dispatched_target_ids,
        "dispatch_errors": dispatch_errors,
        "count": len(dispatched_target_ids),
    }


@app.task
def publish_post_target(post_target_id: str):
    post_target = PostTarget.objects.select_related("post", "social_account__provider").prefetch_related("post__media_items__media_asset").get(pk=post_target_id)
    adapter = get_provider_adapter(post_target.social_account.provider.code)
    if post_target.delivery_status != DeliveryStatus.PUBLISHING:
        post_target.delivery_status = DeliveryStatus.PUBLISHING
        post_target.save(update_fields=["delivery_status", "updated_at"])
    _sync_post_delivery_state(post_target.post)
    request_payload = {
        "caption_text": post_target.post.caption_text,
        "payload": post_target.post.payload,
        "provider_payload_override": post_target.provider_payload_override,
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
        target_account_payload = {
            "external_id": post_target.social_account.external_id,
            "display_name": post_target.social_account.display_name,
            "account_type": post_target.social_account.account_type,
            "access_token": post_target.social_account.metadata.get("access_token", ""),
            "refresh_token": post_target.social_account.metadata.get("refresh_token", ""),
            "page_access_token": post_target.social_account.metadata.get("page_access_token", ""),
            "parent_page_id": post_target.social_account.metadata.get("parent_page_id", ""),
            "username": post_target.social_account.metadata.get("username", ""),
            "avatar_url": post_target.social_account.metadata.get("avatar_url", ""),
            "open_id": post_target.social_account.metadata.get("open_id", ""),
            "publish_options_cache": post_target.social_account.metadata.get("tiktok_publish_options_cache", {}),
        }
        response = adapter.publish_post(
            target_account_payload,
            request_payload,
        )
        response_status = str(response.get("status") or "").lower()
        if response_status == "published":
            _mark_post_target_published(post_target, attempt, response)
        elif response_status == "failed":
            raise ValueError(response.get("error") or "Publishing failed.")
        else:
            post_target.delivery_status = DeliveryStatus.PUBLISHING
            post_target.provider_result = response
            post_target.save(update_fields=["delivery_status", "provider_result", "updated_at"])
            _sync_post_delivery_state(post_target.post)
            attempt.response_payload = response
            attempt.save(update_fields=["response_payload", "updated_at"])
            _schedule_publish_status_poll(str(post_target.id), PUBLISH_STATUS_POLL_ATTEMPTS)
    except Exception as exc:
        _mark_post_target_failed(post_target, attempt, str(exc))


def _mark_post_target_published(post_target: PostTarget, attempt: PublishAttempt, response: dict):
    attempt.status = DeliveryStatus.PUBLISHED
    attempt.response_payload = response
    attempt.finished_at = timezone.now()
    attempt.save()
    post_target.delivery_status = DeliveryStatus.PUBLISHED
    post_target.provider_result = response
    post_target.save(update_fields=["delivery_status", "provider_result", "updated_at"])
    _sync_post_delivery_state(post_target.post)


def _mark_post_target_failed(post_target: PostTarget, attempt: PublishAttempt, error_detail: str, response: dict | None = None):
    attempt.status = DeliveryStatus.FAILED
    attempt.error_detail = error_detail
    if response is not None:
        attempt.response_payload = response
    attempt.finished_at = timezone.now()
    attempt.save()
    post_target.delivery_status = DeliveryStatus.FAILED
    post_target.provider_result = {"error": error_detail, **(response or {})}
    post_target.save(update_fields=["delivery_status", "provider_result", "updated_at"])
    _sync_post_delivery_state(post_target.post)


def _schedule_publish_status_poll(post_target_id: str, attempts_left: int):
    if attempts_left <= 0:
        return
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        time.sleep(PUBLISH_STATUS_POLL_DELAY_SECONDS)
        poll_post_target_status(post_target_id, attempts_left)
        return
    poll_post_target_status.apply_async(args=[post_target_id, attempts_left], countdown=PUBLISH_STATUS_POLL_DELAY_SECONDS)


@app.task
def poll_post_target_status(post_target_id: str, attempts_left: int = PUBLISH_STATUS_POLL_ATTEMPTS):
    post_target = PostTarget.objects.select_related("post", "social_account__provider").get(pk=post_target_id)
    if post_target.delivery_status != DeliveryStatus.PUBLISHING:
        return {"status": post_target.delivery_status}

    adapter = get_provider_adapter(post_target.social_account.provider.code)
    target_account_payload = {
        "external_id": post_target.social_account.external_id,
        "display_name": post_target.social_account.display_name,
        "account_type": post_target.social_account.account_type,
        "access_token": post_target.social_account.metadata.get("access_token", ""),
        "refresh_token": post_target.social_account.metadata.get("refresh_token", ""),
        "page_access_token": post_target.social_account.metadata.get("page_access_token", ""),
        "parent_page_id": post_target.social_account.metadata.get("parent_page_id", ""),
        "username": post_target.social_account.metadata.get("username", ""),
        "avatar_url": post_target.social_account.metadata.get("avatar_url", ""),
        "open_id": post_target.social_account.metadata.get("open_id", ""),
        "publish_options_cache": post_target.social_account.metadata.get("tiktok_publish_options_cache", {}),
    }
    attempt = PublishAttempt.objects.filter(post_target=post_target).order_by("-created_at").first()
    provider_result = post_target.provider_result or {}
    try:
        response = adapter.get_publish_status(target_account_payload, provider_result)
    except Exception as exc:
        if attempts_left > 1 and _is_transient_publish_status_error(post_target, exc):
            _schedule_publish_status_poll(post_target_id, attempts_left - 1)
            return {"status": "publishing", "attempts_left": attempts_left - 1}
        if attempt is None:
            attempt = PublishAttempt.objects.create(
                post_target=post_target,
                status=DeliveryStatus.PUBLISHING,
                request_payload={},
            )
        _mark_post_target_failed(post_target, attempt, str(exc), provider_result)
        return {"status": "failed", "error": str(exc)}

    response_status = str(response.get("status") or "").lower()
    post_target.provider_result = response
    post_target.save(update_fields=["provider_result", "updated_at"])
    if attempt is not None:
        attempt.response_payload = response
        attempt.save(update_fields=["response_payload", "updated_at"])

    if response_status == "published":
        if attempt is None:
            attempt = PublishAttempt.objects.create(post_target=post_target, status=DeliveryStatus.PUBLISHING, request_payload={})
        _mark_post_target_published(post_target, attempt, response)
        return {"status": "published"}

    if response_status == "failed":
        if attempt is None:
            attempt = PublishAttempt.objects.create(post_target=post_target, status=DeliveryStatus.PUBLISHING, request_payload={})
        _mark_post_target_failed(post_target, attempt, response.get("error") or "Publishing failed.", response)
        return {"status": "failed", "error": response.get("error") or "Publishing failed."}

    if attempts_left > 1:
        _schedule_publish_status_poll(post_target_id, attempts_left - 1)
        return {"status": "publishing", "attempts_left": attempts_left - 1}

    if attempt is None:
        attempt = PublishAttempt.objects.create(post_target=post_target, status=DeliveryStatus.PUBLISHING, request_payload={})
    timeout_message = f"Publishing confirmation timed out after {PUBLISH_STATUS_POLL_ATTEMPTS} checks."
    _mark_post_target_failed(post_target, attempt, timeout_message, response)
    return {"status": "failed", "error": timeout_message}
