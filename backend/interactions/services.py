from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from analytics.models import ProviderSyncState, ProviderSyncStatus, ProviderSyncType
from analytics.services import build_account_adapter_payload, is_meta_supported_account
from publishing.models import DeliveryStatus, PostTarget
from social.adapters import get_provider_adapter, interaction_capabilities_for_account, interaction_adapter_code
from social.models import SocialAccount

from .models import InteractionDirection, InteractionMessage, InteractionThread, InteractionThreadType


def account_interaction_capabilities(account: SocialAccount) -> dict[str, bool]:
    return interaction_capabilities_for_account(
        provider_code=account.provider.code,
        account_type=account.account_type,
    )


def account_supports_inbox_comments(account: SocialAccount) -> bool:
    return bool(account_interaction_capabilities(account).get("inbox_comments"))


def account_supports_comment_replies(account: SocialAccount) -> bool:
    return bool(account_interaction_capabilities(account).get("reply_comments"))


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

    if not account_supports_inbox_comments(account) or not is_meta_supported_account(account):
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
            thread = InteractionThread.objects.filter(
                workspace=account.workspace,
                social_account=account,
                thread_type=InteractionThreadType.COMMENTS,
                external_object_id=str(provider_post_id),
            ).first()
            has_existing_messages = InteractionMessage.objects.filter(thread=thread).exists() if thread else False
            cursor = (thread.sync_cursor or None) if thread and has_existing_messages else None
            since = thread.last_synced_at if thread and has_existing_messages else None
            comments = adapter.fetch_object_comments(
                payload,
                str(provider_post_id),
                cursor=cursor,
                since=since,
            )
            if not comments.get("comments") and thread is None:
                continue
            if not comments.get("comments") and thread and not has_existing_messages:
                thread.delete()
                continue
            if thread is None:
                thread = InteractionThread.objects.create(
                    workspace=account.workspace,
                    social_account=account,
                    post_target=post_target,
                    thread_type=InteractionThreadType.COMMENTS,
                    external_object_id=str(provider_post_id),
                    metadata={"provider_post_id": provider_post_id},
                )
            else:
                thread_updates: list[str] = []
                if thread.post_target_id != post_target.id:
                    thread.post_target = post_target
                    thread_updates.append("post_target")
                metadata = dict(thread.metadata or {})
                if metadata.get("provider_post_id") != provider_post_id:
                    metadata["provider_post_id"] = provider_post_id
                    thread.metadata = metadata
                    thread_updates.append("metadata")
                if thread_updates:
                    thread.save(update_fields=[*thread_updates, "updated_at"])
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


def reply_to_thread_comment(*, thread: InteractionThread, parent_message: InteractionMessage, body_text: str, user) -> InteractionMessage:
    account = thread.social_account
    if parent_message.thread_id != thread.id:
        raise ValidationError({"parent_message_id": "Reply target must belong to the same thread."})
    if parent_message.direction != InteractionDirection.INBOUND:
        raise ValidationError({"parent_message_id": "Replies can only target inbound messages."})
    if not account_supports_comment_replies(account):
        raise ValidationError({"detail": "Comment replies are not supported for this channel."})

    payload = build_account_adapter_payload(account)
    adapter = get_provider_adapter(interaction_adapter_code(account.provider.code, account.account_type))
    result = adapter.reply_to_comment(payload, parent_message.external_id, body_text.strip())
    published_at = result.get("published_at") or timezone.now()
    author_name = (
        result.get("author_name")
        or account.display_name
        or user.get_full_name().strip()
        or getattr(user, "username", "")
        or "Workspace"
    )
    message = InteractionMessage.objects.create(
        thread=thread,
        parent_message=parent_message,
        external_id=result.get("external_id") or f"{parent_message.external_id}-reply-{int(published_at.timestamp())}",
        parent_external_id=parent_message.external_id,
        author_name=author_name,
        author_external_id=result.get("author_external_id", ""),
        body_text=result.get("body_text") or body_text.strip(),
        direction=InteractionDirection.OUTBOUND,
        published_at=published_at,
        metadata=result.get("metadata") or {},
    )
    thread.last_message_at = published_at
    thread.save(update_fields=["last_message_at", "updated_at"])
    return message


def comment_on_community_post(*, account: SocialAccount, external_object_id: str, body_text: str, user) -> InteractionMessage:
    if not account_supports_inbox_comments(account) or not is_meta_supported_account(account):
        raise ValidationError({"detail": "Commenting on posts is not supported for this channel."})

    payload = build_account_adapter_payload(account)
    adapter = get_provider_adapter(interaction_adapter_code(account.provider.code, account.account_type))
    result = adapter.comment_on_post(payload, str(external_object_id), body_text.strip())
    published_at = result.get("published_at") or timezone.now()
    author_name = (
        result.get("author_name")
        or account.display_name
        or user.get_full_name().strip()
        or getattr(user, "username", "")
        or "Workspace"
    )
    thread, _ = InteractionThread.objects.get_or_create(
        workspace=account.workspace,
        social_account=account,
        thread_type=InteractionThreadType.COMMENTS,
        external_object_id=str(external_object_id),
        defaults={"metadata": {"provider_post_id": external_object_id}},
    )
    message = InteractionMessage.objects.create(
        thread=thread,
        external_id=result.get("external_id") or f"{external_object_id}-comment-{int(published_at.timestamp())}",
        parent_external_id="",
        author_name=author_name,
        author_external_id=result.get("author_external_id", "") or str(account.external_id),
        body_text=result.get("body_text") or body_text.strip(),
        direction=InteractionDirection.OUTBOUND,
        published_at=published_at,
        metadata=result.get("metadata") or {},
    )
    thread.last_message_at = published_at
    thread.last_synced_at = published_at
    metadata = dict(thread.metadata or {})
    if metadata.get("provider_post_id") != str(external_object_id):
        metadata["provider_post_id"] = str(external_object_id)
        thread.metadata = metadata
        thread.save(update_fields=["last_message_at", "last_synced_at", "metadata", "updated_at"])
    else:
        thread.save(update_fields=["last_message_at", "last_synced_at", "updated_at"])
    return message


def inbox_thread_queryset_for_workspace(workspace, *, status_value=None, account_id=None, platform=None):
    queryset = (
        InteractionThread.objects.filter(workspace=workspace)
        .select_related("social_account", "social_account__provider", "post_target__post")
        .annotate(message_count=Count("messages"), max_message_at=Max("messages__published_at"))
        .filter(message_count__gt=0)
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


def _community_adapter_for_account(account: SocialAccount):
    return get_provider_adapter(interaction_adapter_code(account.provider.code, account.account_type))


def _thread_for_external_object(*, account: SocialAccount, external_object_id: str) -> InteractionThread | None:
    return (
        InteractionThread.objects.filter(
            workspace=account.workspace,
            social_account=account,
            thread_type=InteractionThreadType.COMMENTS,
            external_object_id=str(external_object_id),
        )
        .select_related("post_target__post")
        .first()
    )


def _message_direction_for_account(account: SocialAccount, item: dict) -> str:
    author_external_id = str(item.get("author_external_id") or "")
    if author_external_id and author_external_id == str(account.external_id):
        return InteractionDirection.OUTBOUND
    username = str(item.get("metadata", {}).get("username") or "")
    if username and username == str(account.metadata.get("username") or ""):
        return InteractionDirection.OUTBOUND
    return InteractionDirection.INBOUND


def _community_post_payload(*, account: SocialAccount, provider_post: dict, thread: InteractionThread | None) -> dict:
    published_at = provider_post.get("published_at")
    last_activity_at = thread.last_message_at if thread and thread.last_message_at else published_at
    body_text = provider_post.get("body_text") or ""
    local_comment_count = thread.messages.count() if thread else 0
    comment_count = max(int(provider_post.get("comment_count") or 0), local_comment_count)
    return {
        "external_object_id": str(provider_post.get("external_object_id") or ""),
        "thread_id": thread.id if thread else None,
        "related_post_id": getattr(thread.post_target, "post_id", None) if thread and thread.post_target_id else None,
        "account_id": account.id,
        "account_name": account.display_name,
        "platform": account.metadata.get("channel_code") or account.provider.code,
        "title": provider_post.get("title") or (body_text.strip().splitlines()[0] if body_text.strip() else account.display_name),
        "body_text": body_text,
        "snippet": (body_text.strip()[:160] + ("..." if len(body_text.strip()) > 160 else "")) if body_text.strip() else "",
        "published_at": published_at,
        "last_activity_at": last_activity_at,
        "permalink_url": provider_post.get("permalink_url", ""),
        "preview_image_url": provider_post.get("preview_image_url", ""),
        "comment_count": comment_count,
        "triage_status": thread.triage_status if thread else "idle",
        "interaction_capabilities": account_interaction_capabilities(account),
    }


def community_posts_for_account(account: SocialAccount, *, limit: int = 25) -> list[dict]:
    if not account_supports_inbox_comments(account) or not is_meta_supported_account(account):
        return []

    payload = build_account_adapter_payload(account)
    adapter = _community_adapter_for_account(account)
    provider_posts = adapter.fetch_community_posts(payload, limit=limit)
    thread_map = {
        thread.external_object_id: thread
        for thread in InteractionThread.objects.filter(
            workspace=account.workspace,
            social_account=account,
            thread_type=InteractionThreadType.COMMENTS,
        ).select_related("post_target__post")
    }

    items = [
        _community_post_payload(
            account=account,
            provider_post=item,
            thread=thread_map.get(str(item.get("external_object_id") or "")),
        )
        for item in provider_posts
    ]
    items = [item for item in items if item["comment_count"] > 0]
    items.sort(key=lambda item: item.get("last_activity_at") or timezone.now(), reverse=True)
    return items


def community_post_detail_for_account(account: SocialAccount, *, external_object_id: str) -> dict:
    if not account_supports_inbox_comments(account) or not is_meta_supported_account(account):
        raise ValidationError({"detail": "Community is not supported for this channel."})

    payload = build_account_adapter_payload(account)
    adapter = _community_adapter_for_account(account)
    provider_post = adapter.fetch_community_post_detail(payload, str(external_object_id))
    thread = _thread_for_external_object(account=account, external_object_id=external_object_id)
    base_payload = _community_post_payload(account=account, provider_post=provider_post, thread=thread)
    comments_payload = adapter.fetch_object_comments(payload, str(external_object_id), cursor=None, since=None)
    local_messages_by_external_id = {
        item.external_id: item
        for item in (thread.messages.all() if thread else [])
    }
    messages = []
    for index, item in enumerate(comments_payload.get("comments", []), start=1):
        local_message = local_messages_by_external_id.get(item.get("external_id") or "")
        messages.append(
            {
                "id": str(local_message.id) if local_message else (item.get("external_id") or f"{external_object_id}-{index}"),
                "external_id": item.get("external_id") or "",
                "parent_external_id": item.get("parent_external_id", ""),
                "author_name": item.get("author_name", "Unknown"),
                "author_external_id": item.get("author_external_id", ""),
                "body_text": item.get("body_text", ""),
                "direction": local_message.direction if local_message else _message_direction_for_account(account, item),
                "published_at": local_message.published_at if local_message else (item.get("published_at") or timezone.now()),
                "metadata": local_message.metadata if local_message else (item.get("metadata") or {}),
            }
        )
    return {
        **base_payload,
        "messages": messages,
        "comment_count": max(base_payload["comment_count"], len(messages)),
        "last_activity_at": messages[-1]["published_at"] if messages else base_payload["last_activity_at"],
    }
