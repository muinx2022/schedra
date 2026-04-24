from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .adapters import get_provider_adapter
from common.security import encrypt_value
from .models import QueueSlot, SocialAccount, SocialConnection, SocialProvider, SocialProviderCode
from .serializers import (
    ConnectAccountSerializer,
    OAuthCallbackSerializer,
    OAuthStartSerializer,
    QueueSlotSerializer,
    QueueSlotWriteSerializer,
    SocialAccountSerializer,
    SocialConnectionSerializer,
)


PROVIDER_DEFAULTS = {
    SocialProviderCode.FACEBOOK: {
        "name": "Facebook",
        "capabilities": {
            "account_types": ["page"],
            "content_types": ["feed_post"],
            "images": True,
        },
    },
    SocialProviderCode.INSTAGRAM: {
        "name": "Instagram",
        "capabilities": {
            "account_types": ["instagram_business"],
            "content_types": ["feed_post", "carousel"],
            "images": True,
        },
    },
    SocialProviderCode.LINKEDIN: {
        "name": "LinkedIn",
        "capabilities": {
            "account_types": ["personal", "organization"],
            "content_types": ["feed_post"],
            "images": True,
        },
    },
    SocialProviderCode.TIKTOK: {
        "name": "TikTok",
        "capabilities": {
            "account_types": ["tiktok_creator"],
            "content_types": ["feed_post"],
            "images": True,
        },
    },
    SocialProviderCode.YOUTUBE: {
        "name": "YouTube",
        "capabilities": {
            "account_types": ["youtube_channel"],
            "content_types": ["video"],
            "images": False,
        },
    },
    SocialProviderCode.PINTEREST: {
        "name": "Pinterest",
        "capabilities": {
            "account_types": ["pinterest_board"],
            "content_types": ["feed_post", "carousel"],
            "images": True,
        },
    },
}


def ensure_default_queue_slots(account: SocialAccount):
    defaults = [
        (0, "09:00"),
        (2, "09:00"),
        (4, "09:00"),
    ]
    for position, (weekday, local_time) in enumerate(defaults):
        QueueSlot.objects.get_or_create(
            social_account=account,
            weekday=weekday,
            local_time=local_time,
            defaults={"position": position},
        )


class SocialConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SocialConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SocialConnection.objects.filter(workspace=self.request.user.workspace).select_related("provider")

    def _get_provider(self, provider_code: str) -> SocialProvider:
        provider, _ = SocialProvider.objects.get_or_create(
            code=provider_code,
            defaults=PROVIDER_DEFAULTS[provider_code],
        )
        return provider

    def _provider_connection(self, request, provider_code: str):
        provider = self._get_provider(provider_code)
        connection, _ = SocialConnection.objects.get_or_create(
            workspace=request.user.workspace,
            provider=provider,
            defaults={"status": "pending"},
        )
        return provider, connection

    def _adapter_error_response(self, exc: Exception):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def _upsert_account_from_payload(self, request, provider, connection, account_payload: dict) -> SocialAccount:
        metadata = {**account_payload["metadata"]}
        if metadata.get("page_access_token"):
            metadata["page_access_token"] = encrypt_value(metadata["page_access_token"])
        if metadata.get("access_token"):
            metadata["access_token"] = encrypt_value(metadata["access_token"])
        # Propagate refresh_token from connection so adapters can refresh expired tokens
        if connection.refresh_token and not metadata.get("refresh_token"):
            metadata["refresh_token"] = connection.refresh_token  # already encrypted
        defaults = {
            "connection": connection,
            "provider": provider,
            "account_type": account_payload["account_type"],
            "display_name": account_payload["display_name"],
            "timezone": account_payload["timezone"],
            "metadata": metadata,
        }
        account = SocialAccount.objects.filter(
            workspace=request.user.workspace,
            provider=provider,
            external_id=account_payload["external_id"],
            account_type=account_payload["account_type"],
        ).first()
        if account:
            for field, value in defaults.items():
                setattr(account, field, value)
            account.save()
        else:
            account = SocialAccount.objects.create(
                workspace=request.user.workspace,
                external_id=account_payload["external_id"],
                **defaults,
            )
        ensure_default_queue_slots(account)
        return account

    def _start_connection(self, request, provider_code: str):
        serializer = OAuthStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider, connection = self._provider_connection(request, provider_code)
        state = get_random_string(24)
        redirect_uri = serializer.validated_data["redirect_uri"]
        adapter = get_provider_adapter(provider.code)
        try:
            authorize_url, extra_meta = adapter.prepare_start(redirect_uri, state)
        except Exception as exc:
            return self._adapter_error_response(exc)
        connection.metadata = {
            **connection.metadata,
            "oauth_state": state,
            "oauth_start_redirect_uri": redirect_uri,
            **extra_meta,
        }
        connection.save(update_fields=["metadata", "updated_at"])
        return Response({"authorize_url": authorize_url, "state": state})

    def _handle_callback(self, request, provider_code: str):
        serializer = OAuthCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider, connection = self._provider_connection(request, provider_code)
        expected_state = (connection.metadata or {}).get("oauth_state")
        if not expected_state or serializer.validated_data["state"] != expected_state:
            return Response({"detail": "Invalid OAuth state."}, status=status.HTTP_400_BAD_REQUEST)
        adapter = get_provider_adapter(provider.code)
        callback_redirect_uri = (connection.metadata or {}).get("oauth_start_redirect_uri") or serializer.validated_data[
            "redirect_uri"
        ]
        try:
            result = adapter.exchange_code(
                serializer.validated_data["code"],
                callback_redirect_uri,
                context=connection.metadata,
            )
        except Exception as exc:
            return self._adapter_error_response(exc)
        encrypted_access_token = encrypt_value(result.access_token)
        encrypted_refresh_token = encrypt_value(result.refresh_token)
        try:
            accounts = adapter.list_accounts(encrypted_access_token)
        except Exception as exc:
            return self._adapter_error_response(exc)
        connection.external_user_id = result.external_user_id
        connection.access_token = encrypted_access_token
        connection.refresh_token = encrypted_refresh_token
        connection.scopes = result.scopes or []
        connection.metadata = result.metadata or {}
        connection.status = "connected"
        connection.save()
        response_payload = {
            "connection": SocialConnectionSerializer(connection).data,
            "accounts": accounts,
        }
        if provider.code == SocialProviderCode.TIKTOK and len(accounts) == 1:
            account = self._upsert_account_from_payload(request, provider, connection, accounts[0])
            response_payload["connected_account"] = SocialAccountSerializer(account).data
        return Response(response_payload)

    def _connect_account(self, request, provider_code: str):
        serializer = ConnectAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider, connection = self._provider_connection(request, provider_code)
        adapter = get_provider_adapter(provider.code)
        try:
            requested_account_type = serializer.validated_data.get("account_type") or ""
            account_payload = next(
                (
                    item
                    for item in adapter.list_accounts(connection.access_token)
                    if item["external_id"] == serializer.validated_data["external_id"]
                    and (not requested_account_type or item.get("account_type") == requested_account_type)
                ),
                None,
            )
        except Exception as exc:
            return self._adapter_error_response(exc)
        if not account_payload:
            return Response({"detail": f"{provider.name} account not found."}, status=status.HTTP_404_NOT_FOUND)
        account = self._upsert_account_from_payload(request, provider, connection, account_payload)
        return Response(SocialAccountSerializer(account).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="facebook/start")
    def facebook_start(self, request):
        return self._start_connection(request, SocialProviderCode.FACEBOOK)

    @action(detail=False, methods=["post"], url_path="facebook/callback")
    def facebook_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.FACEBOOK)

    @action(detail=False, methods=["post"], url_path="facebook/connect-account")
    def facebook_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.FACEBOOK)

    @action(detail=False, methods=["post"], url_path="instagram/start")
    def instagram_start(self, request):
        return self._start_connection(request, SocialProviderCode.INSTAGRAM)

    @action(detail=False, methods=["post"], url_path="instagram/callback")
    def instagram_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.INSTAGRAM)

    @action(detail=False, methods=["post"], url_path="instagram/connect-account")
    def instagram_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.INSTAGRAM)

    @action(detail=False, methods=["post"], url_path="linkedin/start")
    def linkedin_start(self, request):
        return self._start_connection(request, SocialProviderCode.LINKEDIN)

    @action(detail=False, methods=["post"], url_path="linkedin/callback")
    def linkedin_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.LINKEDIN)

    @action(detail=False, methods=["post"], url_path="linkedin/connect-account")
    def linkedin_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.LINKEDIN)

    @action(detail=False, methods=["post"], url_path="tiktok/start")
    def tiktok_start(self, request):
        return self._start_connection(request, SocialProviderCode.TIKTOK)

    @action(detail=False, methods=["post"], url_path="tiktok/callback")
    def tiktok_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.TIKTOK)

    @action(detail=False, methods=["post"], url_path="tiktok/connect-account")
    def tiktok_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.TIKTOK)

    @action(detail=False, methods=["post"], url_path="youtube/start")
    def youtube_start(self, request):
        return self._start_connection(request, SocialProviderCode.YOUTUBE)

    @action(detail=False, methods=["post"], url_path="youtube/callback")
    def youtube_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.YOUTUBE)

    @action(detail=False, methods=["post"], url_path="youtube/connect-account")
    def youtube_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.YOUTUBE)

    @action(detail=False, methods=["post"], url_path="pinterest/start")
    def pinterest_start(self, request):
        return self._start_connection(request, SocialProviderCode.PINTEREST)

    @action(detail=False, methods=["post"], url_path="pinterest/callback")
    def pinterest_callback(self, request):
        return self._handle_callback(request, SocialProviderCode.PINTEREST)

    @action(detail=False, methods=["post"], url_path="pinterest/connect-account")
    def pinterest_connect_account(self, request):
        return self._connect_account(request, SocialProviderCode.PINTEREST)


class SocialAccountViewSet(viewsets.ModelViewSet):
    serializer_class = SocialAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    TIKTOK_PUBLISH_OPTIONS_CACHE_KEY = "tiktok_publish_options_cache"
    TIKTOK_PUBLISH_OPTIONS_FAST_TIMEOUT = 5

    def get_queryset(self):
        return SocialAccount.objects.filter(workspace=self.request.user.workspace).select_related("provider", "connection")

    def perform_destroy(self, instance):
        instance.delete()

    def _target_account_payload(self, account: SocialAccount) -> dict:
        metadata = account.metadata or {}
        return {
            "external_id": account.external_id,
            "display_name": account.display_name,
            "account_type": account.account_type,
            "access_token": metadata.get("access_token", ""),
            "refresh_token": metadata.get("refresh_token", ""),
            "page_access_token": metadata.get("page_access_token", ""),
            "parent_page_id": metadata.get("parent_page_id", ""),
            "username": metadata.get("username", ""),
            "avatar_url": metadata.get("avatar_url", ""),
            "open_id": metadata.get("open_id", ""),
            "publish_options_cache": metadata.get(self.TIKTOK_PUBLISH_OPTIONS_CACHE_KEY, {}),
        }

    def _tiktok_publish_options_cache(self, account: SocialAccount) -> dict | None:
        metadata = account.metadata or {}
        cache = metadata.get(self.TIKTOK_PUBLISH_OPTIONS_CACHE_KEY)
        return cache if isinstance(cache, dict) else None

    def _store_tiktok_publish_options_cache(self, account: SocialAccount, options: dict) -> None:
        metadata = {**(account.metadata or {})}
        metadata[self.TIKTOK_PUBLISH_OPTIONS_CACHE_KEY] = {
            "fetched_at": timezone.now().timestamp(),
            "data": options,
        }
        account.metadata = metadata
        account.save(update_fields=["metadata", "updated_at"])

    def _default_tiktok_publish_options(self, account: SocialAccount, detail: str = "") -> dict:
        metadata = account.metadata or {}
        payload = {
            "provider": "tiktok",
            "creator": {
                "nickname": account.display_name or "TikTok Creator",
                "username": metadata.get("username", ""),
                "avatar_url": metadata.get("avatar_url", ""),
            },
            "privacy_level_options": [
                "PUBLIC_TO_EVERYONE",
                "FOLLOWER_OF_CREATOR",
                "MUTUAL_FOLLOW_FRIENDS",
                "SELF_ONLY",
            ],
            "comment_disabled": False,
            "duet_disabled": False,
            "stitch_disabled": False,
            "max_video_post_duration_sec": None,
            "stale": True,
        }
        if detail:
            payload["detail"] = detail
        return payload

    def _queue_slot(self, account: SocialAccount, slot_id: str) -> QueueSlot:
        return get_object_or_404(QueueSlot, social_account=account, id=slot_id)

    def _validate_no_duplicate_queue_slot(
        self,
        account: SocialAccount,
        *,
        weekday: int,
        local_time,
        exclude_slot_id: str | None = None,
    ):
        queryset = QueueSlot.objects.filter(
            social_account=account,
            weekday=weekday,
            local_time=local_time,
        )
        if exclude_slot_id:
            queryset = queryset.exclude(id=exclude_slot_id)
        if queryset.exists():
            return Response(
                {"detail": "A queue slot for this day and time already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=["post"], url_path="queue-slots")
    def create_queue_slot(self, request, pk=None):
        account = self.get_object()
        serializer = QueueSlotWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        duplicate_error = self._validate_no_duplicate_queue_slot(
            account,
            weekday=serializer.validated_data["weekday"],
            local_time=serializer.validated_data["local_time"],
        )
        if duplicate_error:
            return duplicate_error
        slot = QueueSlot.objects.create(social_account=account, **serializer.validated_data)
        return Response(QueueSlotSerializer(slot).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"queue-slots/(?P<slot_id>[^/.]+)")
    def manage_queue_slot(self, request, pk=None, slot_id=None):
        account = self.get_object()
        slot = self._queue_slot(account, slot_id)
        if request.method.lower() == "delete":
            slot.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = QueueSlotWriteSerializer(slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        duplicate_error = self._validate_no_duplicate_queue_slot(
            account,
            weekday=serializer.validated_data.get("weekday", slot.weekday),
            local_time=serializer.validated_data.get("local_time", slot.local_time),
            exclude_slot_id=str(slot.id),
        )
        if duplicate_error:
            return duplicate_error
        serializer.save()
        return Response(QueueSlotSerializer(slot).data)

    @action(detail=True, methods=["get"], url_path="publish-options")
    def publish_options(self, request, pk=None):
        account = self.get_object()
        adapter = get_provider_adapter(account.provider.code)
        if account.provider.code == SocialProviderCode.TIKTOK:
            cache = self._tiktok_publish_options_cache(account)
            payload = self._target_account_payload(account)
            try:
                options = adapter.get_publish_options(payload, timeout=self.TIKTOK_PUBLISH_OPTIONS_FAST_TIMEOUT)
                self._store_tiktok_publish_options_cache(account, options)
                return Response(options)
            except Exception as exc:
                if cache and isinstance(cache.get("data"), dict):
                    cached_options = {**cache["data"], "stale": True, "detail": str(exc)}
                    return Response(cached_options)
                return Response(self._default_tiktok_publish_options(account, str(exc)))
        try:
            options = adapter.get_publish_options(self._target_account_payload(account))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(options)
