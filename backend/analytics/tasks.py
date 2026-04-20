from datetime import timedelta

from django.utils import timezone

from accounts.models import Workspace
from config.celery import app
from social.models import SocialAccount

from .models import (
    ProviderDailyInsight,
    ProviderMetricKey,
    ProviderSyncState,
    ProviderSyncStatus,
    ProviderSyncType,
)
from .services import build_account_adapter_payload, is_meta_supported_account
from social.adapters import get_provider_adapter


INSIGHTS_FIRST_SYNC_DAYS = 30
INSIGHTS_REFRESH_DAYS = 3


def _get_or_create_sync_state(account: SocialAccount, sync_type: str) -> ProviderSyncState:
    state, _ = ProviderSyncState.objects.get_or_create(
        social_account=account,
        sync_type=sync_type,
        defaults={"status": ProviderSyncStatus.IDLE},
    )
    return state


def _sync_window_dates(state: ProviderSyncState, now):
    if state.last_success_at:
        return now.date() - timedelta(days=INSIGHTS_REFRESH_DAYS - 1), now.date()
    return now.date() - timedelta(days=INSIGHTS_FIRST_SYNC_DAYS - 1), now.date()


def sync_provider_insights_for_account(account: SocialAccount) -> dict:
    now = timezone.now()
    state = _get_or_create_sync_state(account, ProviderSyncType.INSIGHTS)
    state.status = ProviderSyncStatus.RUNNING
    state.last_error = ""
    state.last_synced_at = now
    state.save(update_fields=["status", "last_error", "last_synced_at", "updated_at"])

    if not is_meta_supported_account(account):
        state.status = ProviderSyncStatus.IDLE
        state.last_error = "Provider insights sync is only supported for Meta Facebook Pages and Instagram Business accounts."
        state.save(update_fields=["status", "last_error", "updated_at"])
        return {"status": "skipped", "account_id": str(account.id)}

    adapter = get_provider_adapter("facebook" if is_meta_supported_account(account) else account.provider.code)
    since_date, until_date = _sync_window_dates(state, now)

    try:
        normalized_rows = adapter.fetch_daily_insights(
            build_account_adapter_payload(account),
            since_date,
            until_date,
        )
        rows_written = 0
        for row in normalized_rows:
            metric_date = row["date"]
            for metric_key in (
                ProviderMetricKey.IMPRESSIONS,
                ProviderMetricKey.REACH,
                ProviderMetricKey.ENGAGEMENT,
            ):
                ProviderDailyInsight.objects.update_or_create(
                    social_account=account,
                    metric_date=metric_date,
                    metric_key=metric_key,
                    defaults={"value": int(row.get(metric_key, 0) or 0)},
                )
                rows_written += 1
        state.status = ProviderSyncStatus.SUCCESS
        state.last_synced_at = now
        state.last_success_at = now
        state.last_error = ""
        state.cursor_or_checkpoint = until_date.isoformat()
        state.save(
            update_fields=[
                "status",
                "last_synced_at",
                "last_success_at",
                "last_error",
                "cursor_or_checkpoint",
                "updated_at",
            ]
        )
        return {"status": "success", "account_id": str(account.id), "rows_written": rows_written}
    except Exception as exc:
        state.status = ProviderSyncStatus.ERROR
        state.last_synced_at = now
        state.last_error = str(exc)
        state.save(update_fields=["status", "last_synced_at", "last_error", "updated_at"])
        return {"status": "error", "account_id": str(account.id), "error": str(exc)}


@app.task
def sync_provider_insights_workspace(workspace_id: str, account_id: str | None = None):
    workspace = Workspace.objects.get(pk=workspace_id)
    accounts = SocialAccount.objects.filter(workspace=workspace).select_related("provider", "connection")
    if account_id:
        accounts = accounts.filter(pk=account_id)
    results = []
    for account in accounts:
        if not is_meta_supported_account(account):
            continue
        results.append(sync_provider_insights_for_account(account))
    return {"count": len(results), "results": results}


@app.task
def sync_provider_insights_batch():
    payload = []
    for workspace in Workspace.objects.all().only("id"):
        payload.append(sync_provider_insights_workspace.delay(str(workspace.id)))
    return {"queued": len(payload)}
