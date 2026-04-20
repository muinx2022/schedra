from django.db.models import Count, Max, Q
from django.utils import timezone

from analytics.models import ProviderSyncState, ProviderSyncStatus, ProviderSyncType
from analytics.services import build_account_adapter_payload, is_meta_supported_account
from publishing.models import DeliveryStatus, PostTarget
from social.adapters import get_provider_adapter
from social.models import SocialAccount

from .models import InteractionMessage, InteractionThread, InteractionThreadType


def sync_comments_for_account(account: SocialAccount) -> dict:
    now = timezone.now()
    state, _ = ProviderSyncState.objects.get_or_create(
        social_account=account,
        sync_type=ProviderSyncType.COMMENTS,
        defaults={"status": ProviderSyncStatus.IDLE},
    )
    state.status = ProviderSyncStatus.RUNNING
    state.last_error = ""
    state.last_synced_at = now
    state.save(update_fields=["status", "last_error", "last_synced_at", "updated_at"])

    if not is_meta_supported_account(account):
        state.status = ProviderSyncStatus.IDLE
        state.last_error = "Comment sync is only supported for Meta Facebook Pages and Instagram Business accounts."
        state.save(update_fields=["status", "last_error", "updated_at"])
        return {"status": "skipped", "account_id": str(account.id)}

    adapter = get_provider_adapter("facebook" if is_meta_supported_account(account) else account.provider.code)
    payload = build_account_adapter_payload(account)
    post_targets = list(
        PostTarget.objects.filter(
            post__workspace=account.workspace,
            social_account=account,
            delivery_status=DeliveryStatus.PUBLISHED,
        )
        .select_related("post")
        .order_by("-updated_at")
    )

    thread_count = 0
    message_count = 0
    try:
        for post_target in post_targets:
            provider_post_id = (post_target.provider_result or {}).get("provider_post_id")
            if not provider_post_id:
                continue
            thread, _ = InteractionThread.objects.get_or_create(
                workspace=account.workspace,
                social_account=account,
                post_target=post_target,
                thread_type=InteractionThreadType.COMMENTS,
                external_object_id=str(provider_post_id),
                defaults={"metadata": {"provider_post_id": provider_post_id}},
            )
            comments = adapter.fetch_object_comments(
                payload,
                str(provider_post_id),
                cursor=thread.sync_cursor or None,
                since=thread.last_synced_at,
            )
            latest_published_at = thread.last_message_at
            external_map = {}
            created_or_updated = 0
            for item in comments.get("comments", []):
                message, _ = InteractionMessage.objects.update_or_create(
                    thread=thread,
                    external_id=item["external_id"],
                    defaults={
                        "parent_external_id": item.get("parent_external_id", ""),
                        "author_name": item.get("author_name", "Unknown"),
                        "author_external_id": item.get("author_external_id", ""),
                        "body_text": item.get("body_text", ""),
                        "published_at": item["published_at"],
                        "metadata": item.get("metadata", {}),
                    },
                )
                external_map[message.external_id] = message
                latest_published_at = max(latest_published_at, message.published_at) if latest_published_at else message.published_at
                created_or_updated += 1
            if external_map:
                for message in external_map.values():
                    parent = external_map.get(message.parent_external_id)
                    if parent and message.parent_message_id != parent.id:
                        message.parent_message = parent
                        message.save(update_fields=["parent_message", "updated_at"])
            thread.last_synced_at = now
            thread.last_message_at = latest_published_at
            thread.sync_cursor = comments.get("next_cursor", "") or ""
            thread.save(update_fields=["last_synced_at", "last_message_at", "sync_cursor", "updated_at"])
            if created_or_updated:
                thread_count += 1
                message_count += created_or_updated

        state.status = ProviderSyncStatus.SUCCESS
        state.last_synced_at = now
        state.last_success_at = now
        state.last_error = ""
        state.save(update_fields=["status", "last_synced_at", "last_success_at", "last_error", "updated_at"])
        return {
            "status": "success",
            "account_id": str(account.id),
            "thread_count": thread_count,
            "message_count": message_count,
        }
    except Exception as exc:
        state.status = ProviderSyncStatus.ERROR
        state.last_synced_at = now
        state.last_error = str(exc)
        state.save(update_fields=["status", "last_synced_at", "last_error", "updated_at"])
        return {"status": "error", "account_id": str(account.id), "error": str(exc)}


def inbox_thread_queryset_for_workspace(workspace, *, status_value=None, account_id=None, platform=None):
    queryset = (
        InteractionThread.objects.filter(workspace=workspace)
        .select_related("social_account", "social_account__provider", "post_target__post")
        .annotate(message_count=Count("messages"), max_message_at=Max("messages__published_at"))
        .order_by("-last_message_at", "-updated_at")
    )
    if status_value:
        queryset = queryset.filter(triage_status=status_value)
    if account_id:
        queryset = queryset.filter(social_account_id=account_id)
    if platform:
        queryset = queryset.filter(
            Q(social_account__provider__code=platform)
            | Q(social_account__metadata__channel_code=platform)
        )
    return queryset
