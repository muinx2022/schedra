from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db.models import Count
from django.utils import timezone

from .models import ProviderDailyInsight, ProviderMetricKey, ProviderSyncState, ProviderSyncStatus, ProviderSyncType
from publishing.models import DeliveryStatus, PublishAttempt
from social.models import QueueSlot, SocialAccount


RANGE_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

RECENT_FAILURE_LIMIT = 10
PROVIDER_METRIC_KEYS = (
    ProviderMetricKey.IMPRESSIONS,
    ProviderMetricKey.REACH,
    ProviderMetricKey.ENGAGEMENT,
)


def _channel_code(account: SocialAccount) -> str:
    if account.provider.code == "meta":
        if account.account_type == "instagram_business":
            return "instagram"
        return "facebook"
    return account.provider.code


def _success_rate(published_attempts: int, failed_attempts: int) -> int:
    total = published_attempts + failed_attempts
    if total <= 0:
        return 0
    return round((published_attempts / total) * 100)


def is_meta_supported_account(account: SocialAccount) -> bool:
    if account.account_type == "page" and account.provider.code in {"facebook", "meta"}:
        return True
    if account.account_type == "instagram_business" and account.provider.code in {"facebook", "meta", "instagram"}:
        return True
    return False


def build_account_adapter_payload(account: SocialAccount) -> dict:
    return {
        "id": str(account.id),
        "external_id": account.external_id,
        "display_name": account.display_name,
        "account_type": account.account_type,
        "provider_code": account.provider.code,
        "channel_code": _channel_code(account),
        "access_token": account.metadata.get("access_token", ""),
        "refresh_token": account.metadata.get("refresh_token", ""),
        "page_access_token": account.metadata.get("page_access_token", ""),
        "parent_page_id": account.metadata.get("parent_page_id", ""),
        "username": account.metadata.get("username", ""),
    }


def _provider_sync_snapshot(states: list[ProviderSyncState], now: datetime) -> dict:
    if not states:
        return {
            "status": ProviderSyncStatus.IDLE,
            "last_success_at": None,
            "last_error": "",
            "freshness_minutes": None,
        }

    statuses = {state.status for state in states}
    last_success_at = max((state.last_success_at for state in states if state.last_success_at), default=None)
    last_error = next((state.last_error for state in states if state.last_error), "")
    freshness_minutes = None
    if last_success_at:
        freshness_minutes = int((now - last_success_at).total_seconds() // 60)

    if statuses == {ProviderSyncStatus.SUCCESS}:
        status = ProviderSyncStatus.SUCCESS
    elif ProviderSyncStatus.RUNNING in statuses:
        status = ProviderSyncStatus.RUNNING
    elif ProviderSyncStatus.ERROR in statuses and ProviderSyncStatus.SUCCESS in statuses:
        status = "partial"
    elif ProviderSyncStatus.ERROR in statuses:
        status = ProviderSyncStatus.ERROR
    else:
        status = ProviderSyncStatus.IDLE

    return {
        "status": status,
        "last_success_at": last_success_at,
        "last_error": last_error,
        "freshness_minutes": freshness_minutes,
    }


def _build_provider_analytics(
    *,
    accounts: list[SocialAccount],
    start_date,
    days: int,
    generated_at: datetime,
):
    supported_accounts = [account for account in accounts if is_meta_supported_account(account)]
    account_ids = [account.id for account in supported_accounts]
    series_map = {
        start_date + timedelta(days=offset): {
            "date": start_date + timedelta(days=offset),
            "impressions": 0,
            "reach": 0,
            "engagement": 0,
        }
        for offset in range(days)
    }
    channel_values = defaultdict(lambda: {"impressions": 0, "reach": 0, "engagement": 0})

    insight_rows = ProviderDailyInsight.objects.filter(
        social_account_id__in=account_ids,
        metric_date__gte=start_date,
    )
    for row in insight_rows:
        if row.metric_date not in series_map:
            continue
        metric_key = str(row.metric_key)
        series_map[row.metric_date][metric_key] += int(row.value or 0)
        channel_values[str(row.social_account_id)][metric_key] += int(row.value or 0)

    states = list(
        ProviderSyncState.objects.filter(
            social_account_id__in=account_ids,
            sync_type=ProviderSyncType.INSIGHTS,
        ).select_related("social_account")
    )
    state_map = {str(state.social_account_id): state for state in states}

    provider_channels = []
    for account in supported_accounts:
        account_key = str(account.id)
        metrics = channel_values[account_key]
        state = state_map.get(account_key)
        provider_channels.append(
            {
                "account_id": account.id,
                "display_name": account.display_name,
                "channel_code": _channel_code(account),
                "impressions": metrics["impressions"],
                "reach": metrics["reach"],
                "engagement": metrics["engagement"],
                "synced_at": state.last_success_at if state else None,
                "sync_status": state.status if state else ProviderSyncStatus.IDLE,
            }
        )

    provider_channels.sort(
        key=lambda item: (
            -(item["impressions"] + item["reach"] + item["engagement"]),
            item["display_name"].lower(),
        )
    )

    provider_summary = {
        "impressions": sum(item["impressions"] for item in provider_channels),
        "reach": sum(item["reach"] for item in provider_channels),
        "engagement": sum(item["engagement"] for item in provider_channels),
    }

    return {
        "provider_sync": _provider_sync_snapshot(states, generated_at),
        "provider_summary": provider_summary,
        "provider_series": list(series_map.values()),
        "provider_channels": provider_channels,
    }


def build_workspace_analytics(workspace, range_key: str = "30d", account: SocialAccount | None = None) -> dict:
    days = RANGE_DAYS.get(range_key, RANGE_DAYS["30d"])
    tz = ZoneInfo(workspace.timezone or "UTC")
    generated_at = timezone.now()
    local_now = generated_at.astimezone(tz)
    start_date = local_now.date() - timedelta(days=days - 1)
    start_dt_local = datetime.combine(start_date, time.min, tzinfo=tz)
    start_dt_utc = start_dt_local.astimezone(dt_timezone.utc)

    accounts_qs = SocialAccount.objects.filter(workspace=workspace).select_related("provider")
    if account is not None:
        accounts_qs = accounts_qs.filter(pk=account.pk)
    accounts = list(accounts_qs)
    account_ids = [account.id for account in accounts]

    active_queue_slots = QueueSlot.objects.filter(
        social_account_id__in=account_ids,
        is_active=True,
    ).count()

    attempts_qs = (
        PublishAttempt.objects.filter(
            post_target__post__workspace=workspace,
            finished_at__isnull=False,
            finished_at__gte=start_dt_utc,
            status__in=[DeliveryStatus.PUBLISHED, DeliveryStatus.FAILED],
        )
        .select_related("post_target__post", "post_target__social_account__provider")
        .order_by("-finished_at", "-created_at")
    )
    if account is not None:
        attempts_qs = attempts_qs.filter(post_target__social_account=account)
    attempts = list(attempts_qs)

    all_finished_attempts_qs = (
        PublishAttempt.objects.filter(
            post_target__post__workspace=workspace,
            finished_at__isnull=False,
            post_target__social_account_id__in=account_ids,
        )
        .select_related("post_target__social_account__provider")
        .order_by("-finished_at", "-created_at")
    )
    all_finished_attempts = list(all_finished_attempts_qs)

    series_map = {
        start_date + timedelta(days=offset): {
            "date": start_date + timedelta(days=offset),
            "published_attempts": 0,
            "failed_attempts": 0,
        }
        for offset in range(days)
    }
    channel_stats = defaultdict(lambda: {"published_attempts": 0, "failed_attempts": 0})
    last_activity_map: dict[str, datetime] = {}

    for attempt in all_finished_attempts:
        account_key = str(attempt.post_target.social_account_id)
        if account_key not in last_activity_map:
            last_activity_map[account_key] = attempt.finished_at

    recent_failures = []
    for attempt in attempts:
        account_obj = attempt.post_target.social_account
        account_key = str(account_obj.id)

        if attempt.status == DeliveryStatus.PUBLISHED:
            channel_stats[account_key]["published_attempts"] += 1
        elif attempt.status == DeliveryStatus.FAILED:
            channel_stats[account_key]["failed_attempts"] += 1
            if len(recent_failures) < RECENT_FAILURE_LIMIT:
                recent_failures.append(
                    {
                        "post_id": attempt.post_target.post_id,
                        "post_target_id": attempt.post_target_id,
                        "account_id": account_obj.id,
                        "account_name": account_obj.display_name,
                        "finished_at": attempt.finished_at,
                        "error_detail": attempt.error_detail or "Unknown error",
                    }
                )

        local_date = attempt.finished_at.astimezone(tz).date()
        if local_date not in series_map:
            continue
        if attempt.status == DeliveryStatus.PUBLISHED:
            series_map[local_date]["published_attempts"] += 1
        elif attempt.status == DeliveryStatus.FAILED:
            series_map[local_date]["failed_attempts"] += 1

    channels = []
    total_published_attempts = 0
    total_failed_attempts = 0

    queue_slot_map = {
        str(item["social_account_id"]): item["count"]
        for item in QueueSlot.objects.filter(
            social_account_id__in=account_ids,
            is_active=True,
        )
        .values("social_account_id")
        .annotate(count=Count("id"))
    }

    for account_obj in accounts:
        account_key = str(account_obj.id)
        published_attempts = channel_stats[account_key]["published_attempts"]
        failed_attempts = channel_stats[account_key]["failed_attempts"]
        total_published_attempts += published_attempts
        total_failed_attempts += failed_attempts
        channels.append(
            {
                "account_id": account_obj.id,
                "display_name": account_obj.display_name,
                "provider_code": account_obj.provider.code,
                "channel_code": _channel_code(account_obj),
                "active_queue_slots": queue_slot_map.get(account_key, 0),
                "published_attempts": published_attempts,
                "failed_attempts": failed_attempts,
                "success_rate": _success_rate(published_attempts, failed_attempts),
                "last_activity_at": last_activity_map.get(account_key),
            }
        )

    channels.sort(
        key=lambda item: (
            -item["published_attempts"],
            item["failed_attempts"],
            item["display_name"].lower(),
        )
    )

    payload = {
        "source": "internal",
        "generated_at": generated_at,
        "filters": {
            "range": range_key,
            "account_id": account.id if account is not None else None,
            "workspace_timezone": workspace.timezone or "UTC",
        },
        "summary": {
            "connected_channels": len(accounts),
            "active_queue_slots": active_queue_slots,
            "published_attempts": total_published_attempts,
            "failed_attempts": total_failed_attempts,
            "success_rate": _success_rate(total_published_attempts, total_failed_attempts),
        },
        "series": list(series_map.values()),
        "channels": channels,
        "recent_failures": recent_failures,
    }
    payload.update(
        _build_provider_analytics(
            accounts=accounts,
            start_date=start_date,
            days=days,
            generated_at=generated_at,
        )
    )
    return payload
