from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from dataclasses import dataclass
import json
import os
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from common.security import decrypt_value
from back_office.models import SocialProviderSettings


def _agent_log(*args, **kwargs):
    return None


@dataclass
class OAuthExchangeResult:
    external_user_id: str
    access_token: str
    refresh_token: str = ""
    expires_in: int | None = None
    scopes: list[str] | None = None
    metadata: dict[str, Any] | None = None


INTERACTION_CAPABILITY_KEYS = ("inbox_comments", "reply_comments")


class ProviderAdapter:
    provider_code: str

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError

    def prepare_start(self, redirect_uri: str, state: str) -> tuple[str, dict[str, Any]]:
        """Returns (authorize_url, extra_metadata_to_store).
        Adapters that need PKCE or other per-request data override this."""
        return self.get_authorize_url(redirect_uri, state), {}

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        raise NotImplementedError

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        raise NotImplementedError

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def interaction_capabilities(self, target_account: dict[str, Any] | None = None) -> dict[str, bool]:
        return {key: False for key in INTERACTION_CAPABILITY_KEYS}

    def get_publish_options(self, target_account: dict[str, Any]) -> dict[str, Any]:
        return {}

    def get_publish_status(self, target_account: dict[str, Any], provider_result: dict[str, Any]) -> dict[str, Any]:
        return provider_result

    def fetch_daily_insights(self, target_account: dict[str, Any], since_date, until_date) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_object_comments(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
        *,
        cursor: str | None = None,
        since=None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_community_posts(
        self,
        target_account: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_community_post_detail(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def reply_to_comment(
        self,
        target_account: dict[str, Any],
        parent_external_id: str,
        body_text: str,
    ) -> dict[str, Any]:
        raise NotImplementedError("Comment replies are not supported for this provider.")

    def comment_on_post(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
        body_text: str,
    ) -> dict[str, Any]:
        raise NotImplementedError("Post comments are not supported for this provider.")

    def normalize_error(self, error: Exception) -> dict[str, Any]:
        return {"detail": str(error)}


class MetaOAuthMixin:
    provider_code = "meta"

    @property
    def force_mock(self) -> bool:
        return bool(getattr(settings, "SOCIAL_FORCE_MOCK", False))

    @property
    def settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def base_url(self) -> str:
        return self.settings.meta_graph_base_url or "https://graph.facebook.com/v23.0"

    @property
    def auth_url(self) -> str:
        return self.settings.meta_auth_base_url or "https://www.facebook.com/v23.0/dialog/oauth"

    @property
    def app_id(self) -> str:
        return self.settings.meta_app_id

    @property
    def app_secret(self) -> str:
        if self.settings.meta_app_secret_enc:
            return decrypt_value(self.settings.meta_app_secret_enc)
        return ""

    REQUIRED_SCOPES = {
        "pages_show_list",
        "pages_manage_posts",
        "pages_read_engagement",
        "pages_read_user_content",
        "pages_manage_engagement",
    }

    @property
    def scopes(self) -> list[str]:
        raw = self.settings.meta_scopes or (
            "pages_show_list,pages_manage_posts,pages_read_engagement,pages_read_user_content,pages_manage_engagement"
        )
        result = [item.strip() for item in raw.split(",") if item.strip()]
        for required in self.REQUIRED_SCOPES:
            if required not in result:
                result.insert(0, required)
        return result

    def _token_value(self, token: str) -> str:
        if not token:
            return ""
        try:
            return decrypt_value(token)
        except Exception:
            return token

    def _meta_access_token(self, target_account: dict[str, Any]) -> str:
        return self._token_value(
            target_account.get("page_access_token")
            or target_account.get("access_token")
            or ""
        )

    def _fetch_insight_metric_series(
        self,
        *,
        account_id: str,
        access_token: str,
        metric_names: list[str],
        since_date,
        until_date,
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for metric_name in metric_names:
            try:
                payload = self._request(
                    f"/{account_id}/insights",
                    query={
                        "metric": metric_name,
                        "period": "day",
                        "since": since_date.isoformat(),
                        "until": until_date.isoformat(),
                        "access_token": access_token,
                    },
                )
                return payload.get("data", []) or []
            except ValueError as exc:
                last_error = exc
                error_text = str(exc)
                if "valid insights metric" in error_text or "Invalid metric" in error_text:
                    continue
                raise
        if last_error:
            return []
        return []

    def fetch_daily_insights(self, target_account: dict[str, Any], since_date, until_date) -> list[dict[str, Any]]:
        if not self.is_configured:
            rows = []
            current = since_date
            while current <= until_date:
                day_offset = (until_date - current).days
                base = max(0, 240 - (day_offset * 5))
                rows.append(
                    {
                        "date": current,
                        "impressions": base,
                        "reach": max(0, base - 24),
                        "engagement": max(0, round(base * 0.18)),
                    }
                )
                current += timedelta(days=1)
            return rows

        account_id = target_account["external_id"]
        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for provider insights sync.")

        if target_account.get("account_type") == "instagram_business":
            metrics = [
                ("impressions", ["views", "impressions"]),
                ("reach", ["reach"]),
                ("engagement", ["total_interactions", "engagement"]),
            ]
        else:
            metrics = [
                ("impressions", ["views", "page_impressions"]),
                ("reach", ["reach", "page_reach"]),
                ("engagement", ["content_interactions", "page_post_engagements"]),
            ]

        aggregated = {}
        for normalized_key, metric_names in metrics:
            data = self._fetch_insight_metric_series(
                account_id=account_id,
                access_token=access_token,
                metric_names=metric_names,
                since_date=since_date,
                until_date=until_date,
            )
            metric_values = (data[0] or {}).get("values", []) if data else []
            for item in metric_values:
                end_time = item.get("end_time")
                if not end_time:
                    continue
                metric_date = datetime.fromisoformat(end_time.replace("Z", "+00:00")).date()
                if metric_date < since_date or metric_date > until_date:
                    continue
                entry = aggregated.setdefault(
                    metric_date,
                    {"date": metric_date, "impressions": 0, "reach": 0, "engagement": 0},
                )
                value = item.get("value", 0)
                entry[normalized_key] = int(value or 0)

        rows = []
        current = since_date
        while current <= until_date:
            rows.append(
                aggregated.get(
                    current,
                    {"date": current, "impressions": 0, "reach": 0, "engagement": 0},
                )
            )
            current += timedelta(days=1)
        return rows

    def fetch_object_comments(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
        *,
        cursor: str | None = None,
        since=None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            published_at = since or datetime.now(dt_timezone.utc)
            return {
                "comments": [
                    {
                        "external_id": f"{external_object_id}-comment-1",
                        "parent_external_id": "",
                        "author_name": "Demo Customer",
                        "author_external_id": "demo-customer-1",
                        "body_text": "Interested. Can you share pricing?",
                        "published_at": published_at,
                        "metadata": {"mock": True},
                    },
                    {
                        "external_id": f"{external_object_id}-comment-2",
                        "parent_external_id": f"{external_object_id}-comment-1",
                        "author_name": "Demo Customer",
                        "author_external_id": "demo-customer-1",
                        "body_text": "Also curious about turnaround time.",
                        "published_at": published_at,
                        "metadata": {"mock": True},
                    },
                ],
                "next_cursor": "",
            }

        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for comment sync.")

        comments: list[dict[str, Any]] = []
        after = cursor or None
        while True:
            query = {
                "fields": (
                    "id,message,text,from{id,name},username,timestamp,parent{id},"
                    "replies{id,message,text,from{id,name},username,timestamp,parent{id}}"
                ),
                "access_token": access_token,
                "limit": 100,
            }
            if since:
                query["since"] = int(since.timestamp())
            if after:
                query["after"] = after
            payload = self._request(f"/{external_object_id}/comments", query=query)
            for item in payload.get("data", []) or []:
                comments.append(self._normalize_meta_comment(item))
                replies = (item.get("replies") or {}).get("data", []) or []
                for reply in replies:
                    normalized = self._normalize_meta_comment(reply)
                    if not normalized.get("parent_external_id"):
                        normalized["parent_external_id"] = item.get("id", "")
                    comments.append(normalized)
            after = ((payload.get("paging") or {}).get("cursors") or {}).get("after")
            if not ((payload.get("paging") or {}).get("next") and after):
                break

        return {"comments": comments, "next_cursor": after or ""}

    def fetch_community_posts(
        self,
        target_account: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        if not self.is_configured:
            now = timezone.now()
            return [
                {
                    "external_object_id": f"mock-post-{index}",
                    "title": f"Mock post {index + 1}",
                    "body_text": f"Demo provider post {index + 1}",
                    "published_at": now - timedelta(hours=index),
                    "permalink_url": "",
                    "preview_image_url": "",
                    "comment_count": index + 1,
                }
                for index in range(min(limit, 3))
            ]

        account_id = target_account["external_id"]
        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for community posts.")

        if target_account.get("account_type") == "instagram_business":
            payload = self._request(
                f"/{account_id}/media",
                query={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,comments_count",
                    "access_token": access_token,
                    "limit": limit,
                },
            )
            return [self._normalize_instagram_media(item) for item in (payload.get("data") or [])]

        payload = self._request(
            f"/{account_id}/posts",
            query={
                "fields": "id,message,created_time,permalink_url,full_picture,comments.summary(true).limit(0)",
                "access_token": access_token,
                "limit": limit,
            },
        )
        return [self._normalize_facebook_post(item) for item in (payload.get("data") or [])]

    def fetch_community_post_detail(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
    ) -> dict[str, Any]:
        if not self.is_configured:
            posts = self.fetch_community_posts(target_account, limit=10)
            return next((item for item in posts if item["external_object_id"] == external_object_id), posts[0] if posts else {})

        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for community post detail.")

        if target_account.get("account_type") == "instagram_business":
            payload = self._request(
                f"/{external_object_id}",
                query={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,comments_count",
                    "access_token": access_token,
                },
            )
            return self._normalize_instagram_media(payload)

        payload = self._request(
            f"/{external_object_id}",
            query={
                "fields": "id,message,created_time,permalink_url,full_picture,comments.summary(true).limit(0)",
                "access_token": access_token,
            },
        )
        return self._normalize_facebook_post(payload)

    def _normalize_facebook_post(self, item: dict[str, Any]) -> dict[str, Any]:
        published_at = item.get("created_time")
        if published_at:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            published_at = timezone.now()
        body_text = item.get("message") or ""
        comment_count = (((item.get("comments") or {}).get("summary") or {}).get("total_count")) or 0
        return {
            "external_object_id": str(item.get("id") or ""),
            "title": (body_text.strip().splitlines()[0] if body_text.strip() else "Facebook post"),
            "body_text": body_text,
            "published_at": published_at,
            "permalink_url": item.get("permalink_url", ""),
            "preview_image_url": item.get("full_picture", ""),
            "comment_count": int(comment_count or 0),
        }

    def _normalize_instagram_media(self, item: dict[str, Any]) -> dict[str, Any]:
        published_at = item.get("timestamp")
        if published_at:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            published_at = timezone.now()
        body_text = item.get("caption") or ""
        preview_image_url = item.get("thumbnail_url") or item.get("media_url") or ""
        return {
            "external_object_id": str(item.get("id") or ""),
            "title": (body_text.strip().splitlines()[0] if body_text.strip() else "Instagram post"),
            "body_text": body_text,
            "published_at": published_at,
            "permalink_url": item.get("permalink", ""),
            "preview_image_url": preview_image_url,
            "comment_count": int(item.get("comments_count") or 0),
        }

    def _normalize_meta_comment(self, item: dict[str, Any]) -> dict[str, Any]:
        author = item.get("from") or {}
        published_at = item.get("timestamp")
        if published_at:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            published_at = datetime.now(dt_timezone.utc)
        parent = item.get("parent") or {}
        return {
            "external_id": str(item.get("id") or ""),
            "parent_external_id": str(parent.get("id") or item.get("parent_id") or ""),
            "author_name": author.get("name") or item.get("username") or "Unknown",
            "author_external_id": str(author.get("id") or ""),
            "body_text": item.get("message") or item.get("text") or "",
            "published_at": published_at,
            "metadata": {"username": item.get("username", "")},
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret) and not self.force_mock

    def _request(
        self,
        path: str,
        query: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ):
        query = query or {}
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        payload = None
        headers = {"Accept": "application/json"}
        if data is not None:
            payload = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _request_multipart(
        self,
        path: str,
        *,
        fields: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        query: dict[str, Any] | None = None,
        method: str = "POST",
    ):
        query = query or {}
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        boundary = f"----SchedraBoundary{int(time.time() * 1000)}"
        payload = self._encode_multipart_payload(boundary, fields or {}, files or {})
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _encode_multipart_payload(
        self,
        boundary: str,
        fields: dict[str, Any],
        files: dict[str, tuple[str, bytes, str]],
    ) -> bytes:
        parts: list[bytes] = []
        boundary_bytes = boundary.encode("utf-8")

        for name, value in fields.items():
            parts.extend(
                [
                    b"--" + boundary_bytes + b"\r\n",
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )

        for name, (filename, content, content_type) in files.items():
            parts.extend(
                [
                    b"--" + boundary_bytes + b"\r\n",
                    (
                        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                        f"Content-Type: {content_type}\r\n\r\n"
                    ).encode("utf-8"),
                    content,
                    b"\r\n",
                ]
            )

        parts.append(b"--" + boundary_bytes + b"--\r\n")
        return b"".join(parts)

    def fetch_remote_media_bytes(self, file_url: str) -> tuple[bytes, str]:
        try:
            with urlopen(file_url) as response:
                content = response.read()
                content_type = (response.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
        except (HTTPError, URLError, OSError) as exc:
            raise ValueError(f"Could not fetch media for provider upload. {exc}") from exc

        if not content:
            raise ValueError("Could not fetch media for provider upload. Remote file is empty.")

        return content, content_type or "application/octet-stream"

    def _load_local_media_asset_bytes(self, media_asset_id: str) -> tuple[bytes, str] | None:
        from media_library.models import MediaAsset

        asset = MediaAsset.objects.filter(pk=media_asset_id).first()
        if not asset or asset.storage_backend != "local" or not asset.file:
            return None

        try:
            with asset.file.open("rb") as fh:
                content = fh.read()
        except OSError as exc:
            raise ValueError(f"Could not read local media for provider upload. {exc}") from exc

        if not content:
            raise ValueError("Could not read local media for provider upload. Local file is empty.")

        content_type = (asset.content_type or "application/octet-stream").split(";")[0].strip()
        return content, content_type or "application/octet-stream"

    def fetch_media_bytes(self, media_item: dict[str, Any]) -> tuple[bytes, str]:
        file_url = (media_item.get("file_url") or "").strip()
        remote_error: ValueError | None = None
        if file_url:
            try:
                return self.fetch_remote_media_bytes(file_url)
            except ValueError as exc:
                remote_error = exc

        media_asset_id = str(media_item.get("id") or "").strip()
        if media_asset_id:
            local_result = self._load_local_media_asset_bytes(media_asset_id)
            if local_result is not None:
                return local_result

        if remote_error is not None:
            raise remote_error

        raise ValueError("Could not fetch media for provider upload. Missing media URL and local asset.")

    def should_retry_media_with_direct_upload(self, exc: Exception) -> bool:
        return False

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_configured:
            return f"{self.auth_url}?{urlencode({'redirect_uri': redirect_uri, 'state': state, 'mock': 'true'})}"
        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.scopes),
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def _http_error_message(self, exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            message = payload.get("error_message")
            code = payload.get("code")
            error_type = payload.get("error_type")
            if message:
                suffix = f" ({error_type} {code})" if error_type or code else ""
                return f"{message}{suffix}"
            error = payload.get("error") or {}
            if isinstance(error, dict):
                message = error.get("message")
                code = error.get("code")
                error_type = error.get("type")
                if message:
                    suffix = f" ({error_type} {code})" if error_type or code else ""
                    return f"{message}{suffix}"
        return f"HTTP Error {exc.code}: {exc.reason}"

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_configured:
            return OAuthExchangeResult(
                external_user_id=f"meta-user-{code}",
                access_token=f"mock-access-token-{code}",
                scopes=self.scopes,
                metadata={"redirect_uri": redirect_uri, "mock": True},
            )
        token_payload = self._request(
            "/oauth/access_token",
            query={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        access_token = token_payload["access_token"]
        long_lived_payload = self._request(
            "/oauth/access_token",
            query={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": access_token,
            },
        )
        me = self._request("/me", query={"fields": "id,name", "access_token": long_lived_payload["access_token"]})
        return OAuthExchangeResult(
            external_user_id=me["id"],
            access_token=long_lived_payload["access_token"],
            expires_in=long_lived_payload.get("expires_in"),
            scopes=self.scopes,
            metadata={"redirect_uri": redirect_uri, "user_name": me.get("name", "")},
        )

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        if not self.is_configured:
            return [
                {
                    "external_id": "fb-page-1",
                    "display_name": "Demo Facebook Page",
                    "account_type": "page",
                    "timezone": "Asia/Saigon",
                    "metadata": {
                        "channel_code": "facebook",
                        "page_access_token": access_token,
                    },
                },
                {
                    "external_id": "ig-business-1",
                    "display_name": "Demo Instagram Business",
                    "account_type": "instagram_business",
                    "timezone": "Asia/Saigon",
                    "metadata": {
                        "channel_code": "instagram",
                        "page_access_token": access_token,
                        "parent_page_id": "fb-page-1",
                        "username": "demo_instagram",
                    },
                },
            ]

        decrypted_access_token = decrypt_value(access_token)
        payload = self._request(
            "/me/accounts",
            query={
                "fields": "id,name,access_token,category,tasks,instagram_business_account{id,username,profile_picture_url}",
                "access_token": decrypted_access_token,
                "limit": 200,
            },
        )
        accounts: list[dict[str, Any]] = []
        
        while True:
            batch = payload.get("data", []) or []
            for item in batch:
                page_token = item.get("access_token", "")
                accounts.append(
                    {
                        "external_id": item["id"],
                        "display_name": item["name"],
                        "account_type": "page",
                        "timezone": "Asia/Saigon",
                        "metadata": {
                            "channel_code": "facebook",
                            "category": item.get("category"),
                            "tasks": item.get("tasks", []),
                            "page_access_token": page_token,
                        },
                    }
                )

                instagram = item.get("instagram_business_account") or {}
                if instagram.get("id"):
                    accounts.append(
                        {
                            "external_id": instagram["id"],
                            "display_name": instagram.get("username") or f"{item['name']} Instagram",
                            "account_type": "instagram_business",
                            "timezone": "Asia/Saigon",
                            "metadata": {
                                "channel_code": "instagram",
                                "username": instagram.get("username", ""),
                                "profile_picture_url": instagram.get("profile_picture_url", ""),
                                "parent_page_id": item["id"],
                                "parent_page_name": item["name"],
                                "page_access_token": page_token,
                            },
                        }
                    )
            
            next_url = (payload.get("paging") or {}).get("next")
            if not next_url:
                break
            after = ((payload.get("paging") or {}).get("cursors") or {}).get("after")
            if not after:
                break
            payload = self._request(
                "/me/accounts",
                query={
                    "fields": "id,name,access_token,category,tasks,instagram_business_account{id,username,profile_picture_url}",
                    "access_token": decrypted_access_token,
                    "limit": 200,
                    "after": after,
                },
            )
        return accounts

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        if not self.is_configured:
            return {"valid": bool(access_token), "provider": "meta", "mock": True}
        payload = self._request("/me", query={"fields": "id", "access_token": decrypt_value(access_token)})
        return {"valid": bool(payload.get("id")), "provider": "meta", "external_user_id": payload.get("id")}

    def _fetch_page_payload(self, access_token: str) -> list[dict[str, Any]]:
        if not self.is_configured:
            return [
                {
                    "id": "fb-page-1",
                    "name": "Demo Facebook Page",
                    "access_token": access_token,
                    "category": "Business",
                    "tasks": ["CREATE_CONTENT", "MODERATE"],
                    "connected_instagram_account": {
                        "id": "ig-business-1",
                        "username": "demo_instagram",
                        "name": "Demo Instagram",
                        "profile_picture_url": "",
                    },
                    "instagram_business_account": {
                        "id": "ig-business-1",
                        "username": "demo_instagram",
                        "profile_picture_url": "",
                    },
                }
            ]

        decrypted_access_token = decrypt_value(access_token)
        pages: list[dict] = []
        query: dict = {
            "fields": (
                "id,name,access_token,category,tasks,"
                "instagram_business_account{id,username,name,profile_picture_url},"
                "connected_instagram_account{id,username,name,profile_picture_url}"
            ),
            "access_token": decrypted_access_token,
            "limit": 200,
        }
        while True:
            payload = self._request("/me/accounts", query=query)
            batch = payload.get("data", []) or []
            pages.extend(batch)
            next_url = (payload.get("paging") or {}).get("next")
            if not next_url:
                break
            # Extract cursor for next page
            after = ((payload.get("paging") or {}).get("cursors") or {}).get("after")
            if not after:
                break
            query = {**query, "after": after}

        # #region agent log — simple accounts probe (no nested fields)
        try:
            simple = self._request(
                "/me/accounts",
                query={"fields": "id,name,tasks", "access_token": decrypted_access_token, "limit": 200},
            )
            _agent_log(
                hypothesis_id="F",
                location="backend/social/adapters.py:MetaOAuthMixin._fetch_page_payload",
                message="Simple /me/accounts (no nested fields)",
                data={
                    "data_len": len(simple.get("data", [])),
                    "pages": [{"id": p.get("id"), "name": p.get("name"), "tasks": p.get("tasks")} for p in simple.get("data", [])],
                },
            )
        except Exception as exc:
            _agent_log(hypothesis_id="F", location="backend/social/adapters.py", message="simple accounts probe failed", data={"error": str(exc)})
        # #endregion

        return pages


class FacebookAdapter(MetaOAuthMixin, ProviderAdapter):
    provider_code = "facebook"

    def interaction_capabilities(self, target_account: dict[str, Any] | None = None) -> dict[str, bool]:
        return {"inbox_comments": True, "reply_comments": True}

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return self._publish_facebook_page(target_account, payload)

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        accounts: list[dict[str, Any]] = []
        for item in self._fetch_page_payload(access_token):
            page_token = item.get("access_token", access_token)
            accounts.append(
                {
                    "external_id": item["id"],
                    "display_name": item["name"],
                    "account_type": "page",
                    "timezone": "Asia/Saigon",
                    "metadata": {
                        "category": item.get("category"),
                        "tasks": item.get("tasks", []),
                        "page_access_token": page_token,
                    },
                }
            )
        return accounts

    def _publish_facebook_page(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured:
            return {
                "provider_post_id": f"fb-post-{target_account['external_id']}",
                "status": "published",
                "echo": payload,
                "mock": True,
            }

        page_id = target_account["external_id"]
        access_token = decrypt_value(target_account.get("page_access_token", ""))
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        if len(media_items) == 1:
            response = self._publish_facebook_photo(
                page_id,
                access_token,
                media_items[0],
                message=caption,
            )
        elif len(media_items) > 1:
            media_ids = []
            for item in media_items:
                photo = self._publish_facebook_photo(
                    page_id,
                    access_token,
                    item,
                    published="false",
                )
                media_ids.append({"media_fbid": photo["id"]})

            feed_payload: dict[str, Any] = {
                "message": caption,
                "access_token": access_token,
            }
            for i, m in enumerate(media_ids):
                feed_payload[f"attached_media[{i}]"] = json.dumps(m)

            response = self._request(
                f"/{page_id}/feed",
                method="POST",
                data=feed_payload,
            )
        else:
            # Text-only post
            response = self._request(
                f"/{page_id}/feed",
                method="POST",
                data={
                    "message": caption,
                    "access_token": access_token,
                },
            )

        return {
            "provider_post_id": response.get("id"),
            "status": "published",
            "raw": response,
        }

    def _publish_facebook_photo(
        self,
        page_id: str,
        access_token: str,
        media_item: dict[str, Any],
        *,
        message: str | None = None,
        published: str | None = None,
    ) -> dict[str, Any]:
        file_url = media_item["file_url"]
        payload: dict[str, Any] = {
            "url": file_url,
            "access_token": access_token,
        }
        if message is not None:
            payload["message"] = message
        if published is not None:
            payload["published"] = published

        try:
            return self._request(
                f"/{page_id}/photos",
                method="POST",
                data=payload,
            )
        except ValueError as exc:
            if not self.should_retry_media_with_direct_upload(exc):
                raise

        content, content_type = self.fetch_media_bytes(media_item)
        multipart_fields: dict[str, Any] = {"access_token": access_token}
        if message is not None:
            multipart_fields["message"] = message
        if published is not None:
            multipart_fields["published"] = published

        return self._request_multipart(
            f"/{page_id}/photos",
            fields=multipart_fields,
            files={"source": ("upload", content, content_type)},
        )

    def should_retry_media_with_direct_upload(self, exc: Exception) -> bool:
        message = str(exc)
        return "Missing or invalid image file" in message or "OAuthException 324" in message

    def reply_to_comment(
        self,
        target_account: dict[str, Any],
        parent_external_id: str,
        body_text: str,
    ) -> dict[str, Any]:
        message_text = body_text.strip()
        if not message_text:
            raise ValueError("Reply text cannot be empty.")

        if not self.is_configured:
            return {
                "external_id": f"{parent_external_id}-reply-{int(timezone.now().timestamp())}",
                "body_text": message_text,
                "published_at": timezone.now(),
                "metadata": {"mock": True},
            }

        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for comment replies.")

        response = self._request(
            f"/{parent_external_id}/comments",
            method="POST",
            data={
                "message": message_text,
                "access_token": access_token,
            },
        )
        return {
            "external_id": str(response.get("id") or ""),
            "body_text": message_text,
            "published_at": timezone.now(),
            "metadata": {"raw": response},
        }

    def comment_on_post(
        self,
        target_account: dict[str, Any],
        external_object_id: str,
        body_text: str,
    ) -> dict[str, Any]:
        message_text = body_text.strip()
        if not message_text:
            raise ValueError("Comment text cannot be empty.")

        if not self.is_configured:
            return {
                "external_id": f"{external_object_id}-comment-{int(timezone.now().timestamp())}",
                "body_text": message_text,
                "published_at": timezone.now(),
                "metadata": {"mock": True},
            }

        access_token = self._meta_access_token(target_account)
        if not access_token:
            raise ValueError("Missing Meta page or account access token for post comments.")

        response = self._request(
            f"/{external_object_id}/comments",
            method="POST",
            data={
                "message": message_text,
                "access_token": access_token,
            },
        )
        return {
            "external_id": str(response.get("id") or ""),
            "body_text": message_text,
            "published_at": timezone.now(),
            "metadata": {"raw": response},
        }


class InstagramAdapter(ProviderAdapter):
    provider_code = "instagram"

    @property
    def settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def app_id(self) -> str:
        return self.settings.instagram_app_id

    @property
    def app_secret(self) -> str:
        if self.settings.instagram_app_secret_enc:
            return decrypt_value(self.settings.instagram_app_secret_enc)
        return ""

    @property
    def auth_url(self) -> str:
        return self.settings.instagram_auth_base_url or "https://www.instagram.com/oauth/authorize"

    @property
    def token_url(self) -> str:
        return self.settings.instagram_token_base_url or "https://api.instagram.com/oauth/access_token"

    @property
    def base_url(self) -> str:
        return self.settings.instagram_graph_base_url or "https://graph.instagram.com"

    REQUIRED_SCOPES = {"instagram_business_basic"}

    @property
    def scopes(self) -> list[str]:
        raw = self.settings.instagram_scopes or "instagram_business_basic,instagram_business_content_publish"
        result = [item.strip() for item in raw.split(",") if item.strip()]
        for required in self.REQUIRED_SCOPES:
            if required not in result:
                result.insert(0, required)
        return result

    @property
    def is_direct_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def _http_error_message(self, exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            message = payload.get("error_message")
            code = payload.get("code")
            error_type = payload.get("error_type")
            if message:
                suffix = f" ({error_type} {code})" if error_type or code else ""
                return f"{message}{suffix}"
            error = payload.get("error") or {}
            if isinstance(error, dict):
                message = error.get("message")
                code = error.get("code")
                error_type = error.get("type")
                if message:
                    suffix = f" ({error_type} {code})" if error_type or code else ""
                    return f"{message}{suffix}"
        return f"HTTP Error {exc.code}: {exc.reason}"

    def _direct_request(
        self,
        path: str,
        query: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ):
        query = query or {}
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        payload = None
        headers = {"Accept": "application/json"}
        if data is not None:
            payload = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _fetch_direct_profile(self, access_token: str) -> dict[str, Any]:
        field_sets = [
            "user_id,username,name,profile_picture_url,followers_count,follows_count,media_count",
            "user_id,username,media_count",
            "id,username,account_type,media_count",
            "id,username",
        ]
        last_error: Exception | None = None
        for fields in field_sets:
            try:
                profile = self._direct_request(
                    "/me",
                    query={"fields": fields, "access_token": access_token},
                )
                profile["_requested_fields"] = fields
                return profile
            except Exception as exc:
                last_error = exc
                _agent_log(
                    hypothesis_id="I",
                    location="backend/social/adapters.py:InstagramAdapter._fetch_direct_profile",
                    message="Instagram direct profile request failed",
                    data={"fields": fields, "error": str(exc)},
                )
        if last_error:
            raise last_error
        raise ValueError("Instagram profile request failed.")

    def _direct_token_exchange(self, code: str, redirect_uri: str) -> dict[str, Any]:
        _agent_log(
            hypothesis_id="I",
            location="backend/social/adapters.py:InstagramAdapter._direct_token_exchange",
            message="Instagram token exchange request",
            data={
                "token_url": self.token_url,
                "app_id": self.app_id,
                "redirect_uri": redirect_uri,
                "code_prefix": code[:12],
            },
        )
        payload = urlencode(
            {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            }
        ).encode("utf-8")
        request = Request(
            self.token_url,
            data=payload,
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request) as response:
                token_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            _agent_log(
                hypothesis_id="I",
                location="backend/social/adapters.py:InstagramAdapter._direct_token_exchange",
                message="Instagram token exchange failed",
                data={
                    "redirect_uri": redirect_uri,
                    "code_prefix": code[:12],
                    "error": self._http_error_message(exc),
                },
            )
            raise ValueError(self._http_error_message(exc)) from exc

        access_token = token_payload.get("access_token", "")
        if not access_token:
            return token_payload

        try:
            long_lived_payload = self._direct_request(
                "/access_token",
                query={
                    "grant_type": "ig_exchange_token",
                    "client_secret": self.app_secret,
                    "access_token": access_token,
                },
            )
            if long_lived_payload.get("access_token"):
                token_payload = {
                    **token_payload,
                    **long_lived_payload,
                    "access_token": long_lived_payload["access_token"],
                }
        except Exception:
            pass
        return token_payload

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_direct_configured:
            raise ValueError(
                "Instagram Login is not configured. Set instagram_app_id and instagram_app_secret in Back Office first."
            )
        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.scopes),
            "response_type": "code",
            "enable_fb_login": "0",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_direct_configured:
            raise ValueError(
                "Instagram Login is not configured. Set instagram_app_id and instagram_app_secret in Back Office first."
            )

        payload = self._direct_token_exchange(code, redirect_uri)
        access_token = payload.get("access_token", "")
        user_id = str(payload.get("user_id") or payload.get("id") or "")

        if not user_id and access_token:
            try:
                me = self._fetch_direct_profile(access_token)
                user_id = str(me.get("user_id") or me.get("id") or "")
                payload = {
                    **payload,
                    "username": me.get("username", ""),
                    "account_type": me.get("account_type", ""),
                    "requested_fields": me.get("_requested_fields", ""),
                }
            except Exception:
                pass

        if not access_token or not user_id:
            raise ValueError("Instagram OAuth did not return a usable access token.")

        return OAuthExchangeResult(
            external_user_id=user_id,
            access_token=access_token,
            expires_in=payload.get("expires_in"),
            scopes=self.scopes,
            metadata={
                "redirect_uri": redirect_uri,
                "username": payload.get("username", ""),
                "account_type": payload.get("account_type", ""),
                "direct_instagram": True,
            },
        )

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        if not self.is_direct_configured:
            raise ValueError(
                "Instagram Login is not configured. Set instagram_app_id and instagram_app_secret in Back Office first."
            )
        decrypted_access_token = decrypt_value(access_token)
        try:
            payload = self._fetch_direct_profile(decrypted_access_token)
            return {
                "valid": bool(payload.get("user_id") or payload.get("id")),
                "provider": "instagram",
                "external_user_id": payload.get("user_id") or payload.get("id"),
                "direct": True,
            }
        except Exception as exc:
            return {"valid": False, "provider": "instagram", "direct": True, "detail": str(exc)}

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        if not self.is_direct_configured:
            raise ValueError(
                "Instagram Login is not configured. Set instagram_app_id and instagram_app_secret in Back Office first."
            )

        decrypted_access_token = decrypt_value(access_token)
        # #region agent log
        _agent_log(
            hypothesis_id="I",
            location="backend/social/adapters.py:InstagramAdapter.list_accounts",
            message="Instagram direct list_accounts start",
            data={"base_url": self.base_url, "scopes": self.scopes, "scopes_count": len(self.scopes)},
        )
        # #endregion
        try:
            me = self._fetch_direct_profile(decrypted_access_token)
        except Exception as exc:
            _agent_log(
                hypothesis_id="I",
                location="backend/social/adapters.py:InstagramAdapter.list_accounts",
                message="Instagram direct /me failed",
                data={"error": str(exc)},
            )
            return []

        external_user_id = me.get("user_id") or me.get("id")
        if not external_user_id:
            return []

        account_type = (me.get("account_type") or "").lower()
        if account_type and account_type not in {"business", "creator"}:
            _agent_log(
                hypothesis_id="I",
                location="backend/social/adapters.py:InstagramAdapter.list_accounts",
                message="Instagram direct account type is not professional",
                data={"account_type": account_type, "user_id": me.get("id")},
            )
            return []

        return [
            {
                "external_id": str(external_user_id),
                "display_name": me.get("username") or "Instagram account",
                "account_type": "instagram_business",
                "timezone": "Asia/Saigon",
                "metadata": {
                    "channel_code": "instagram",
                    "username": me.get("username", ""),
                    "account_type": me.get("account_type", ""),
                    "access_token": decrypted_access_token,
                },
            }
        ]

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_direct_configured:
            raise ValueError(
                "Instagram Login is not configured. Set instagram_app_id and instagram_app_secret in Back Office first."
            )
        return self._publish_instagram(target_account, payload)

    def _publish_instagram(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        media_items = payload.get("media_items") or []
        mode = ((payload.get("payload") or {}).get("feed_post") or {}).get("mode") or "single"
        if not self.is_direct_configured:
            return {
                "provider_post_id": f"ig-post-{target_account['external_id']}",
                "status": "published",
                "mode": mode,
                "media_count": len(media_items),
                "echo": payload,
                "mock": True,
            }

        access_token = decrypt_value(target_account.get("access_token") or target_account.get("page_access_token", ""))
        caption_text = payload.get("caption_text", "")
        self._validate_public_media_urls(media_items)

        if mode == "carousel":
            children = []
            for item in media_items:
                children.append(self._create_instagram_media_container(
                    target_account["external_id"],
                    item["file_url"],
                    access_token,
                    is_carousel_item=True,
                ))
            creation = self._direct_request(
                f"/{target_account['external_id']}/media",
                method="POST",
                data={
                    "caption": caption_text,
                    "media_type": "CAROUSEL",
                    "children": ",".join(children),
                    "access_token": access_token,
                },
            )
        else:
            creation = self._direct_request(
                f"/{target_account['external_id']}/media",
                method="POST",
                data={
                    "image_url": media_items[0]["file_url"],
                    "caption": caption_text,
                    "access_token": access_token,
                },
            )

        self._wait_for_container(creation["id"], access_token)

        publish = self._direct_request(
            f"/{target_account['external_id']}/media_publish",
            method="POST",
            data={
                "creation_id": creation["id"],
                "access_token": access_token,
            },
        )
        return {
            "provider_post_id": publish.get("id"),
            "creation_id": creation.get("id"),
            "status": "published",
            "mode": mode,
            "raw": {"creation": creation, "publish": publish},
        }

    def _wait_for_container(
        self,
        container_id: str,
        access_token: str,
        max_attempts: int = 15,
        interval: float = 3.0,
    ) -> None:
        for attempt in range(max_attempts):
            result = self._direct_request(
                f"/{container_id}",
                query={"fields": "status_code", "access_token": access_token},
            )
            status = result.get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ValueError("Instagram media container processing failed.")
            if status == "EXPIRED":
                raise ValueError("Instagram media container expired before publishing.")
            time.sleep(interval)
        raise ValueError("Instagram media container did not finish processing in time.")

    def _create_instagram_media_container(
        self,
        instagram_account_id: str,
        file_url: str,
        access_token: str,
        *,
        is_carousel_item: bool,
    ) -> str:
        data = {
            "image_url": file_url,
            "access_token": access_token,
        }
        if is_carousel_item:
            data["is_carousel_item"] = "true"
        response = self._direct_request(
            f"/{instagram_account_id}/media",
            method="POST",
            data=data,
        )
        return response["id"]

    def _validate_public_media_urls(self, media_items: list[dict[str, Any]]) -> None:
        for item in media_items:
            file_url = (item.get("file_url") or "").strip()
            if not file_url.startswith(("http://", "https://")):
                raise ValueError(
                    "Instagram publishing requires public absolute media URLs. "
                    "Configure a public media base URL or use a public storage backend."
                )


class LinkedInAdapter(ProviderAdapter):
    provider_code = "linkedin"

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE = "https://api.linkedin.com/v2"

    @property
    def settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def client_id(self) -> str:
        return self.settings.linkedin_client_id

    @property
    def client_secret(self) -> str:
        if self.settings.linkedin_client_secret_enc:
            return decrypt_value(self.settings.linkedin_client_secret_enc)
        return ""

    @property
    def scopes(self) -> list[str]:
        raw = self.settings.linkedin_scopes or "openid,profile,email,w_member_social,w_organization_social,r_organization_admin"
        return [s.strip() for s in raw.split(",") if s.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _api(
        self,
        path: str,
        access_token: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        headers_extra: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            **(headers_extra or {}),
        }
        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
                err = json.loads(body)
                message = err.get("message") or err.get("error_description") or str(err)
            except Exception:
                message = f"HTTP {exc.code}"
            raise ValueError(message) from exc

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_configured:
            raise ValueError("LinkedIn is not configured. Set linkedin_client_id and linkedin_client_secret in Back Office.")
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(self.scopes),
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_configured:
            raise ValueError("LinkedIn is not configured.")
        payload = urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode("utf-8")
        request = Request(
            self.TOKEN_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        try:
            with urlopen(request) as response:
                token = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                err = json.loads(exc.read().decode("utf-8"))
                msg = err.get("error_description") or str(err)
            except Exception:
                msg = f"HTTP {exc.code}"
            raise ValueError(msg) from exc

        access_token = token["access_token"]
        profile = self._api("/userinfo", access_token)
        user_id = str(profile.get("sub") or profile.get("id") or "")
        return OAuthExchangeResult(
            external_user_id=user_id,
            access_token=access_token,
            expires_in=token.get("expires_in"),
            scopes=self.scopes,
            metadata={
                "name": profile.get("name", ""),
                "email": profile.get("email", ""),
                "picture": profile.get("picture", ""),
            },
        )

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise ValueError("LinkedIn is not configured.")
        token = decrypt_value(access_token)
        profile = self._api("/userinfo", token)
        user_id = str(profile.get("sub") or profile.get("id") or "")
        accounts = [{
            "external_id": user_id,
            "display_name": profile.get("name") or profile.get("email") or "LinkedIn Account",
            "account_type": "personal",
            "timezone": "Asia/Saigon",
            "metadata": {
                "channel_code": "linkedin",
                "access_token": token,
                "picture": profile.get("picture", ""),
            },
        }]
        try:
            accounts.extend(self._list_organization_accounts(token))
        except Exception:
            # Keep personal profile usable even when organization scopes are unavailable.
            pass
        return accounts

    def _list_organization_accounts(self, access_token: str) -> list[dict[str, Any]]:
        acl_payload = self._api(
            "/organizationAcls",
            access_token,
            query={"q": "roleAssignee", "state": "APPROVED"},
        )
        allowed_roles = {"ADMINISTRATOR", "CONTENT_ADMIN", "DIRECT_SPONSORED_CONTENT_POSTER"}
        organization_ids: list[str] = []
        for item in acl_payload.get("elements", []) or []:
            if item.get("role") not in allowed_roles:
                continue
            organization_urn = str(item.get("organization") or "")
            if not organization_urn.startswith("urn:li:organization:"):
                continue
            organization_id = organization_urn.rsplit(":", 1)[-1]
            if organization_id and organization_id not in organization_ids:
                organization_ids.append(organization_id)

        accounts: list[dict[str, Any]] = []
        for organization_id in organization_ids:
            profile = self._api(f"/organizations/{organization_id}", access_token)
            display_name = (
                profile.get("localizedName")
                or ((profile.get("name") or {}).get("localized") or {}).get("en_US")
                or f"LinkedIn Page {organization_id}"
            )
            accounts.append(
                {
                    "external_id": organization_id,
                    "display_name": display_name,
                    "account_type": "organization",
                    "timezone": "Asia/Saigon",
                    "metadata": {
                        "channel_code": "linkedin",
                        "access_token": access_token,
                        "organization_urn": f"urn:li:organization:{organization_id}",
                        "vanity_name": profile.get("vanityName", ""),
                    },
                }
            )
        return accounts

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        try:
            token = decrypt_value(access_token)
            profile = self._api("/userinfo", token)
            return {"valid": bool(profile.get("sub") or profile.get("id")), "provider": "linkedin"}
        except Exception as exc:
            return {"valid": False, "provider": "linkedin", "detail": str(exc)}

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        access_token = decrypt_value(target_account.get("access_token", ""))
        if target_account.get("account_type") == "organization":
            author_urn = target_account.get("organization_urn") or f"urn:li:organization:{target_account['external_id']}"
        else:
            author_urn = f"urn:li:person:{target_account['external_id']}"
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        if media_items:
            # Upload each image then attach
            image_urns = [self._upload_image(access_token, item, author_urn) for item in media_items]
            content: dict[str, Any] = {
                "media": [
                    {"status": "READY", "media": urn, "title": {"text": ""}}
                    for urn in image_urns
                ],
                "shareMediaCategory": "IMAGE" if len(image_urns) == 1 else "IMAGE",
            }
        else:
            content = {"shareMediaCategory": "NONE"}

        ugc: dict[str, Any] = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    **content,
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        result = self._api("/ugcPosts", access_token, method="POST", data=ugc)
        return {
            "provider_post_id": result.get("id"),
            "status": "published",
            "raw": result,
        }

    def _upload_image(self, access_token: str, media_item: dict[str, Any], owner_urn: str) -> str:
        # Step 1: Register upload
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": owner_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }],
            }
        }
        reg = self._api("/assets?action=registerUpload", access_token, method="POST", data=register_body)
        upload_url = reg["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = reg["value"]["asset"]

        # Step 2: Fetch image bytes and PUT to upload URL
        image_data, _ = self.fetch_media_bytes(media_item)

        upload_req = Request(upload_url, data=image_data, method="PUT", headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
        })
        with urlopen(upload_req):
            pass

        return asset_urn


class TikTokAdapter(ProviderAdapter):
    provider_code = "tiktok"
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    API_BASE = "https://open.tiktokapis.com/v2"
    REQUEST_TIMEOUT = 60
    RETRYABLE_REQUEST_ATTEMPTS = 2
    RETRYABLE_REQUEST_DELAY = 1.0
    PUBLISH_STATUS_REQUEST_TIMEOUT = 5
    PUBLISH_STATUS_RETRYABLE_REQUEST_ATTEMPTS = 1
    USER_AGENT = "Schedra/1.0 (+https://schedra.net)"
    PUBLISH_OPTIONS_CACHE_MAX_AGE = 15 * 60

    @property
    def _settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def client_key(self) -> str:
        return self._settings.tiktok_client_key

    @property
    def client_secret(self) -> str:
        if self._settings.tiktok_client_secret_enc:
            return decrypt_value(self._settings.tiktok_client_secret_enc)
        return ""

    @property
    def scopes(self) -> list[str]:
        raw = self._settings.tiktok_scopes or "user.info.basic,video.publish"
        return [s.strip() for s in raw.split(",") if s.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.client_key and self.client_secret)

    def _generate_pkce(self) -> tuple[str, str]:
        import hashlib, base64, secrets as _secrets
        verifier = _secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    def prepare_start(self, redirect_uri: str, state: str) -> tuple[str, dict[str, Any]]:
        if not self.is_configured:
            raise ValueError("TikTok is not configured. Set tiktok_client_key and tiktok_client_secret in Back Office.")
        verifier, challenge = self._generate_pkce()
        params = {
            "client_key": self.client_key,
            "scope": ",".join(self.scopes),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}", {"tiktok_code_verifier": verifier}

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        url, _ = self.prepare_start(redirect_uri, state)
        return url

    def _http_error_message(self, exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error", {})
            if isinstance(error, dict):
                msg = error.get("message") or error.get("description")
                if msg:
                    return msg
        return f"TikTok HTTP {exc.code}: {exc.reason}"

    def _network_error_message(self, exc: Exception) -> str:
        detail = str(exc) or exc.__class__.__name__
        return f"Could not reach TikTok API from the local backend. {detail}"

    def _is_retryable_network_error(self, exc: Exception) -> bool:
        if isinstance(exc, socket.timeout):
            return True
        if isinstance(exc, TimeoutError):
            return True
        if isinstance(exc, URLError):
            reason = getattr(exc, "reason", None)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                return True
        detail = str(getattr(exc, "reason", exc) or "").lower()
        return "timed out" in detail

    def _urlopen(
        self,
        request: Request,
        timeout: int | float | None = None,
        *,
        retry_attempts: int | None = None,
        retry_delay: float | None = None,
    ):
        last_exc: Exception | None = None
        attempts = retry_attempts if retry_attempts is not None else self.RETRYABLE_REQUEST_ATTEMPTS
        delay = retry_delay if retry_delay is not None else self.RETRYABLE_REQUEST_DELAY
        for attempt in range(1, attempts + 1):
            try:
                return urlopen(request, timeout=timeout or self.REQUEST_TIMEOUT)
            except (URLError, TimeoutError, socket.timeout) as exc:
                last_exc = exc
                if attempt >= attempts or not self._is_retryable_network_error(exc):
                    raise
                time.sleep(delay)
        if last_exc:
            raise last_exc

    def _api(
        self,
        path: str,
        access_token: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int | float | None = None,
        retry_attempts: int | None = None,
        retry_delay: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
        }
        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=UTF-8"
        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with self._urlopen(
                request,
                timeout=timeout,
                retry_attempts=retry_attempts,
                retry_delay=retry_delay,
            ) as response:
                body = response.read().decode("utf-8")
                result = json.loads(body) if body else {}
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise ValueError(self._network_error_message(exc)) from exc
        error = result.get("error", {})
        if isinstance(error, dict) and error.get("code") not in (None, "ok", ""):
            raise ValueError(error.get("message") or f"TikTok error: {error.get('code')}")
        return result

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_configured:
            raise ValueError("TikTok is not configured.")
        code_verifier = (context or {}).get("tiktok_code_verifier", "")
        body: dict[str, Any] = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            body["code_verifier"] = code_verifier
        request = Request(
            self.TOKEN_URL,
            data=urlencode(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": self.USER_AGENT,
            },
        )
        try:
            with self._urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise ValueError(self._network_error_message(exc)) from exc
        # TikTok may wrap in {"data": {...}} or return flat
        data_obj = payload.get("data", payload)
        error_obj = payload.get("error", {})
        if isinstance(error_obj, dict) and error_obj.get("code") not in (None, "ok", ""):
            raise ValueError(error_obj.get("message") or "TikTok token exchange failed")
        access_token = data_obj.get("access_token") or payload.get("access_token")
        refresh_token = data_obj.get("refresh_token") or payload.get("refresh_token", "")
        open_id = data_obj.get("open_id") or payload.get("open_id", "")
        scope_str = data_obj.get("scope") or payload.get("scope", "")
        scopes = [s.strip() for s in scope_str.split(",") if s.strip()] or self.scopes
        return OAuthExchangeResult(
            external_user_id=open_id,
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=scopes,
            metadata={"open_id": open_id},
        )

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise ValueError("TikTok is not configured.")
        token = decrypt_value(access_token)
        fields = ["open_id", "union_id", "display_name", "avatar_url"]
        if "user.info.profile" in self.scopes:
            fields.append("profile_deep_link")
        result = self._api(
            "/user/info/",
            token,
            params={"fields": ",".join(fields)},
        )
        user = (result.get("data") or {}).get("user") or {}
        open_id = user.get("open_id", "")
        display_name = user.get("display_name") or "TikTok Creator"
        return [{
            "external_id": open_id,
            "display_name": display_name,
            "account_type": "tiktok_creator",
            "timezone": "UTC",
            "metadata": {
                "channel_code": "tiktok",
                "access_token": token,
                "avatar_url": user.get("avatar_url", ""),
                "open_id": open_id,
            },
        }]

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        try:
            token = decrypt_value(access_token)
            result = self._api("/user/info/", token, params={"fields": "open_id"})
            user = (result.get("data") or {}).get("user") or {}
            return {"valid": bool(user.get("open_id")), "provider": "tiktok"}
        except Exception as exc:
            return {"valid": False, "provider": "tiktok", "detail": str(exc)}

    def _cached_publish_options(self, target_account: dict[str, Any]) -> dict[str, Any] | None:
        cache = target_account.get("publish_options_cache") or {}
        if not isinstance(cache, dict):
            return None
        payload = cache.get("data")
        fetched_at = cache.get("fetched_at")
        if not isinstance(payload, dict) or fetched_at in (None, ""):
            return None
        try:
            fetched_at_value = float(fetched_at)
        except (TypeError, ValueError):
            return None
        if time.time() - fetched_at_value > self.PUBLISH_OPTIONS_CACHE_MAX_AGE:
            return None
        return payload

    def get_publish_options(self, target_account: dict[str, Any], timeout: int | float | None = None) -> dict[str, Any]:
        cached = self._cached_publish_options(target_account)
        if cached:
            return cached
        access_token = decrypt_value(target_account.get("access_token", ""))
        result = self._api("/post/publish/creator_info/query/", access_token, method="POST", data={}, timeout=timeout)
        data = result.get("data") or {}
        return {
            "provider": "tiktok",
            "creator": {
                "nickname": data.get("creator_nickname") or target_account.get("display_name") or "TikTok Creator",
                "username": data.get("creator_username") or "",
                "avatar_url": data.get("creator_avatar_url") or target_account.get("avatar_url") or "",
            },
            "privacy_level_options": data.get("privacy_level_options") or [],
            "comment_disabled": bool(data.get("comment_disabled")),
            "duet_disabled": bool(data.get("duet_disabled")),
            "stitch_disabled": bool(data.get("stitch_disabled")),
            "max_video_post_duration_sec": data.get("max_video_post_duration_sec"),
        }

    def get_publish_status(self, target_account: dict[str, Any], provider_result: dict[str, Any]) -> dict[str, Any]:
        access_token = decrypt_value(target_account.get("access_token", ""))
        publish_id = provider_result.get("provider_post_id") or ((provider_result.get("raw") or {}).get("data") or {}).get("publish_id")
        if not publish_id:
            raise ValueError("TikTok publish status check requires a publish_id.")
        result = self._api(
            "/post/publish/status/fetch/",
            access_token,
            method="POST",
            data={"publish_id": publish_id},
            timeout=self.PUBLISH_STATUS_REQUEST_TIMEOUT,
            retry_attempts=self.PUBLISH_STATUS_RETRYABLE_REQUEST_ATTEMPTS,
            retry_delay=0,
        )
        data = result.get("data") or {}
        raw_status = str(data.get("status") or "").upper()
        fail_reason = data.get("fail_reason") or data.get("error") or data.get("message") or ""
        status_map = {
            "PROCESSING_UPLOAD": "publishing",
            "PROCESSING_DOWNLOAD": "publishing",
            "PROCESSING_PUBLISH": "publishing",
            "SEND_TO_USER_INBOX": "published",
            "PUBLISH_COMPLETE": "published",
            "FAILED": "failed",
        }
        normalized_status = status_map.get(raw_status, "publishing")
        response = {
            **provider_result,
            "provider_post_id": publish_id,
            "status": normalized_status,
            "raw_status": raw_status,
            "raw": result,
        }
        if fail_reason:
            response["error"] = str(fail_reason)
        if data.get("publicaly_available_post_id"):
            response["external_object_id"] = data.get("publicaly_available_post_id")
        if data.get("uploaded_bytes"):
            response["uploaded_bytes"] = data.get("uploaded_bytes")
        return response

    def _publish_settings(self, target_account: dict[str, Any], payload: dict[str, Any], *, has_video: bool) -> dict[str, Any]:
        publish_options = self.get_publish_options(target_account)
        override = payload.get("provider_payload_override") or {}
        privacy_level = (override.get("privacy_level") or "").strip()
        if not privacy_level:
            raise ValueError("Select a TikTok privacy setting before publishing.")
        allowed_privacy = publish_options.get("privacy_level_options") or []
        if privacy_level not in allowed_privacy:
            raise ValueError("The selected TikTok privacy setting is no longer available. Refresh and try again.")

        if not override.get("consent_confirmed"):
            raise ValueError("TikTok publish requires explicit music usage consent.")

        commercial_content_enabled = bool(override.get("commercial_content_enabled"))
        brand_organic = bool(override.get("brand_organic_toggle"))
        brand_content = bool(override.get("brand_content_toggle"))
        if commercial_content_enabled and not (brand_organic or brand_content):
            raise ValueError("Select at least one TikTok commercial content disclosure option.")
        if brand_content and privacy_level == "SELF_ONLY":
            raise ValueError("TikTok branded content visibility cannot be private.")

        allow_comment = bool(override.get("allow_comment"))
        allow_duet = bool(override.get("allow_duet"))
        allow_stitch = bool(override.get("allow_stitch"))

        if publish_options.get("comment_disabled"):
            allow_comment = False
        if has_video and publish_options.get("duet_disabled"):
            allow_duet = False
        if has_video and publish_options.get("stitch_disabled"):
            allow_stitch = False

        settings = {
            "privacy_level": privacy_level,
            "disable_comment": not allow_comment,
            "brand_content_toggle": brand_content,
            "brand_organic_toggle": brand_organic,
        }
        if has_video:
            settings["disable_duet"] = not allow_duet
            settings["disable_stitch"] = not allow_stitch
        return settings

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        access_token = decrypt_value(target_account.get("access_token", ""))
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        videos = [m for m in media_items if m.get("kind") == "video"]
        images = [m for m in media_items if m.get("kind") != "video"]

        if videos:
            settings = self._publish_settings(target_account, payload, has_video=True)
            return self._publish_video(access_token, caption, videos[0]["file_url"], settings)
        elif images:
            settings = self._publish_settings(target_account, payload, has_video=False)
            return self._publish_photos(access_token, caption, [m["file_url"] for m in images], settings)
        else:
            raise ValueError("TikTok requires at least one image or video.")

    def _publish_photos(self, access_token: str, caption: str, image_urls: list[str], settings: dict[str, Any]) -> dict[str, Any]:
        body = {
            "post_info": {
                "title": caption[:2200],
                "description": caption[:2200],
                "privacy_level": settings["privacy_level"],
                "disable_comment": settings["disable_comment"],
                "brand_content_toggle": settings["brand_content_toggle"],
                "brand_organic_toggle": settings["brand_organic_toggle"],
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_images": image_urls[:35],
                "photo_cover_index": 0,
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        }
        result = self._api("/post/publish/content/init/", access_token, method="POST", data=body)
        publish_id = (result.get("data") or {}).get("publish_id", "")
        return {"provider_post_id": publish_id, "status": "publishing", "raw": result}

    def _publish_video(self, access_token: str, caption: str, video_url: str, settings: dict[str, Any]) -> dict[str, Any]:
        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": settings["privacy_level"],
                "disable_duet": settings["disable_duet"],
                "disable_comment": settings["disable_comment"],
                "disable_stitch": settings["disable_stitch"],
                "brand_content_toggle": settings["brand_content_toggle"],
                "brand_organic_toggle": settings["brand_organic_toggle"],
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
            "post_mode": "DIRECT_POST",
            "media_type": "VIDEO",
        }
        result = self._api("/post/publish/video/init/", access_token, method="POST", data=body)
        publish_id = (result.get("data") or {}).get("publish_id", "")
        return {"provider_post_id": publish_id, "status": "publishing", "raw": result}


class YouTubeAdapter(ProviderAdapter):
    provider_code = "youtube"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://www.googleapis.com/youtube/v3"
    UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"

    @property
    def _settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def client_id(self) -> str:
        return self._settings.youtube_client_id

    @property
    def client_secret(self) -> str:
        if self._settings.youtube_client_secret_enc:
            return decrypt_value(self._settings.youtube_client_secret_enc)
        return ""

    @property
    def scopes(self) -> list[str]:
        raw = self._settings.youtube_scopes or (
            "https://www.googleapis.com/auth/youtube.upload,"
            "https://www.googleapis.com/auth/youtube.readonly"
        )
        return [s.strip() for s in raw.split(",") if s.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_configured:
            raise ValueError("YouTube is not configured. Set youtube_client_id and youtube_client_secret in Back Office.")
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def _http_error_message(self, exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error", {})
            if isinstance(error, dict):
                msg = error.get("message")
                if msg:
                    return msg
            if isinstance(error, str):
                return payload.get("error_description") or error
        return f"YouTube HTTP {exc.code}: {exc.reason}"

    def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.TOKEN_URL,
            data=urlencode(data).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _refresh_access_token(self, refresh_token_enc: str) -> str:
        token = decrypt_value(refresh_token_enc)
        result = self._token_request({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": token,
            "grant_type": "refresh_token",
        })
        return result.get("access_token", "")

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_configured:
            raise ValueError("YouTube is not configured.")
        result = self._token_request({
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        access_token = result.get("access_token", "")
        refresh_token = result.get("refresh_token", "")
        channel = self._get_channel(access_token)
        channel_id = channel.get("id", "")
        channel_title = (channel.get("snippet") or {}).get("title", "")
        return OAuthExchangeResult(
            external_user_id=channel_id,
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=self.scopes,
            metadata={"channel_id": channel_id, "channel_title": channel_title},
        )

    def _api(self, path: str, access_token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _get_channel(self, access_token: str) -> dict[str, Any]:
        result = self._api("/channels", access_token, params={"part": "snippet", "mine": "true"})
        items = result.get("items") or []
        return items[0] if items else {}

    def list_accounts(self, access_token: str) -> list[dict[str, Any]]:
        token = decrypt_value(access_token)
        channel = self._get_channel(token)
        channel_id = channel.get("id", "")
        title = (channel.get("snippet") or {}).get("title") or "YouTube Channel"
        return [{
            "external_id": channel_id,
            "display_name": title,
            "account_type": "youtube_channel",
            "timezone": "UTC",
            "metadata": {
                "channel_code": "youtube",
                "access_token": token,
            },
        }]

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        try:
            token = decrypt_value(access_token)
            channel = self._get_channel(token)
            return {"valid": bool(channel.get("id")), "provider": "youtube"}
        except Exception as exc:
            return {"valid": False, "provider": "youtube", "detail": str(exc)}

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        media_items = payload.get("media_items") or []
        videos = [m for m in media_items if m.get("kind") == "video"]
        if not videos:
            raise ValueError("YouTube requires a video. Image-only posts are not supported.")
        # Prefer refresh token for fresh access (YT tokens expire in 1 hour)
        refresh_token_enc = target_account.get("refresh_token", "")
        if refresh_token_enc:
            access_token = self._refresh_access_token(refresh_token_enc)
        else:
            access_token = decrypt_value(target_account.get("access_token", ""))
        return self._upload_video(access_token, videos[0]["file_url"], payload.get("caption_text", ""))

    def _upload_video(self, access_token: str, video_url: str, caption: str) -> dict[str, Any]:
        with urlopen(video_url) as resp:
            video_bytes = resp.read()
        video_size = len(video_bytes)
        metadata = {
            "snippet": {
                "title": (caption[:100] or "Untitled"),
                "description": caption,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        metadata_bytes = json.dumps(metadata).encode("utf-8")
        init_request = Request(
            f"{self.UPLOAD_BASE}/videos?uploadType=resumable&part=snippet,status",
            data=metadata_bytes,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
                "X-Upload-Content-Length": str(video_size),
            },
        )
        try:
            with urlopen(init_request) as init_resp:
                upload_url = init_resp.headers.get("Location", "")
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
        if not upload_url:
            raise ValueError("YouTube did not return an upload URL.")
        upload_request = Request(
            upload_url,
            data=video_bytes,
            method="PUT",
            headers={"Content-Type": "video/*", "Content-Length": str(video_size)},
        )
        try:
            with urlopen(upload_request) as upload_resp:
                result = json.loads(upload_resp.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
        video_id = result.get("id", "")
        return {"provider_post_id": video_id, "status": "published", "url": f"https://youtu.be/{video_id}", "raw": result}


class PinterestAdapter(ProviderAdapter):
    provider_code = "pinterest"
    AUTH_URL = "https://www.pinterest.com/oauth/"
    DEFAULT_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
    DEFAULT_API_BASE = "https://api.pinterest.com/v5"
    REQUIRED_SCOPES = ["boards:read", "boards:write", "pins:read", "pins:write"]

    @property
    def settings(self) -> SocialProviderSettings:
        return SocialProviderSettings.load()

    @property
    def client_id(self) -> str:
        return self.settings.pinterest_app_id

    @property
    def client_secret(self) -> str:
        if self.settings.pinterest_app_secret_enc:
            return decrypt_value(self.settings.pinterest_app_secret_enc)
        return ""

    @property
    def token_url(self) -> str:
        return os.getenv("PINTEREST_TOKEN_URL", self.DEFAULT_TOKEN_URL).strip() or self.DEFAULT_TOKEN_URL

    @property
    def api_base(self) -> str:
        return os.getenv("PINTEREST_API_BASE_URL", self.DEFAULT_API_BASE).strip().rstrip("/") or self.DEFAULT_API_BASE

    @property
    def publish_api_base(self) -> str:
        return os.getenv("PINTEREST_PUBLISH_API_BASE_URL", "").strip().rstrip("/") or self.api_base

    @property
    def scopes(self) -> list[str]:
        raw = self.settings.pinterest_scopes or ",".join(self.REQUIRED_SCOPES)
        scopes = [s.strip() for s in raw.split(",") if s.strip()]
        for required in self.REQUIRED_SCOPES:
            if required not in scopes:
                scopes.append(required)
        return scopes

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        if not self.is_configured:
            raise ValueError("Pinterest is not configured. Set pinterest_app_id and pinterest_app_secret in Back Office.")
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.scopes),
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def _http_error_message(self, exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            msg = payload.get("message") or payload.get("error_description") or payload.get("error")
            if msg:
                return str(msg)
        return f"Pinterest HTTP {exc.code}: {exc.reason}"

    def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        import base64
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        request = Request(
            self.token_url,
            data=urlencode(data).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def exchange_code(self, code: str, redirect_uri: str, context: dict[str, Any] | None = None) -> OAuthExchangeResult:
        if not self.is_configured:
            raise ValueError("Pinterest is not configured.")
        result = self._token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        })
        access_token = result.get("access_token", "")
        refresh_token = result.get("refresh_token", "")
        return OAuthExchangeResult(
            external_user_id=str(result.get("user_id", "") or ""),
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=self.scopes,
            metadata={},
        )

    def _api(
        self,
        path: str,
        access_token: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        *,
        use_publish_base: bool = False,
    ) -> dict[str, Any]:
        base_url = self.publish_api_base if use_publish_base else self.api_base
        url = f"{base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None
        headers: dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        if body:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc

    def _refresh_access_token(self, refresh_token_enc: str) -> str:
        token = decrypt_value(refresh_token_enc)
        result = self._token_request({
            "grant_type": "refresh_token",
            "refresh_token": token,
        })
        return result.get("access_token", "")

    def list_accounts(self, access_token_enc: str) -> list[dict[str, Any]]:
        token = decrypt_value(access_token_enc)
        url = f"{self.api_base}/boards?page_size=50"
        request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        try:
            with urlopen(request) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
        boards = data.get("items") or []
        return [
            {
                "external_id": board["id"],
                "display_name": board["name"],
                "account_type": "pinterest_board",
                "timezone": "Asia/Saigon",
                "metadata": {
                    "access_token": token,
                    "board_url": board.get("url", ""),
                    "privacy": board.get("privacy", "PUBLIC"),
                },
            }
            for board in boards
        ]

    def validate_credentials(self, access_token_enc: str) -> dict[str, Any]:
        try:
            token = decrypt_value(access_token_enc)
            data = self._api("/user_account", token)
            return {"valid": True, "provider": "pinterest", "username": data.get("username")}
        except Exception as exc:
            return {"valid": False, "provider": "pinterest", "detail": str(exc)}

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        refresh_token_enc = target_account.get("refresh_token", "")
        if refresh_token_enc:
            access_token = self._refresh_access_token(refresh_token_enc)
        else:
            access_token = decrypt_value(target_account.get("access_token", ""))

        board_id = target_account.get("external_id", "")
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        images = [m for m in media_items if m.get("kind") != "video"]
        videos = [m for m in media_items if m.get("kind") == "video"]

        if videos:
            media_id = self._upload_video(access_token, videos[0]["file_url"])
            pin_data: dict[str, Any] = {
                "board_id": board_id,
                "title": caption[:100],
                "description": caption[:500],
                "media_source": {"source_type": "video_id", "media_id": media_id},
            }
        elif len(images) == 1:
            pin_data = {
                "board_id": board_id,
                "title": caption[:100],
                "description": caption[:500],
                "media_source": {"source_type": "image_url", "url": images[0]["file_url"]},
            }
        elif len(images) > 1:
            pin_data = {
                "board_id": board_id,
                "title": caption[:100],
                "description": caption[:500],
                "media_source": {
                    "source_type": "multiple_image_urls",
                    "items": [{"url": img["file_url"]} for img in images[:5]],
                },
            }
        else:
            raise ValueError("Pinterest requires at least one image or video.")

        result = self._api("/pins", access_token, method="POST", data=pin_data, use_publish_base=True)
        return {
            "provider_post_id": result.get("id"),
            "status": "published",
            "url": result.get("link", ""),
            "raw": result,
        }

    def _upload_video(self, access_token: str, video_url: str) -> str:
        # Step 1: Register upload
        reg = self._api("/media", access_token, method="POST", data={"media_type": "video"}, use_publish_base=True)
        media_id = str(reg.get("media_id", ""))
        upload_url = reg.get("upload_url", "")
        upload_parameters: dict[str, str] = reg.get("upload_parameters") or {}

        # Step 2: Fetch video bytes
        with urlopen(video_url) as resp:
            video_bytes = resp.read()

        # Step 3: Multipart POST to S3 pre-signed URL
        import uuid as _uuid
        boundary = _uuid.uuid4().hex.encode()
        body_parts: list[bytes] = []
        for key, value in upload_parameters.items():
            body_parts.append(
                b"--" + boundary + b"\r\n"
                + f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
                + str(value).encode() + b"\r\n"
            )
        body_parts.append(
            b"--" + boundary + b"\r\n"
            + b'Content-Disposition: form-data; name="file"; filename="video.mp4"\r\n'
            + b"Content-Type: video/mp4\r\n\r\n"
            + video_bytes + b"\r\n"
        )
        body_parts.append(b"--" + boundary + b"--\r\n")
        body = b"".join(body_parts)

        upload_req = Request(
            upload_url,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        )
        try:
            with urlopen(upload_req):
                pass
        except HTTPError as exc:
            if exc.code not in (200, 204):
                raise ValueError(f"Pinterest video upload failed: {exc.code}") from exc

        # Step 4: Poll until processing complete (max 60s)
        for _ in range(20):
            time.sleep(3)
            status_data = self._api(f"/media/{media_id}", access_token, use_publish_base=True)
            if status_data.get("status") == "succeeded":
                return media_id
            if status_data.get("status") == "failed":
                raise ValueError("Pinterest video processing failed.")
        raise ValueError("Pinterest video processing timed out. Try again in a moment.")


def get_provider_adapter(provider_code: str) -> ProviderAdapter:
    if provider_code == "facebook":
        return FacebookAdapter()
    if provider_code == "instagram":
        return InstagramAdapter()
    if provider_code == "meta":
        return FacebookAdapter()
    if provider_code == "linkedin":
        return LinkedInAdapter()
    if provider_code == "tiktok":
        return TikTokAdapter()
    if provider_code == "youtube":
        return YouTubeAdapter()
    if provider_code == "pinterest":
        return PinterestAdapter()
    raise ValueError(f"Unsupported provider: {provider_code}")


def interaction_adapter_code(provider_code: str, account_type: str) -> str:
    normalized_provider = str(provider_code or "").lower()
    normalized_account_type = str(account_type or "").lower()
    if normalized_account_type in {"page", "instagram_business"} and normalized_provider in {"facebook", "meta", "instagram"}:
        return "facebook"
    return normalized_provider


def interaction_capabilities_for_account(*, provider_code: str, account_type: str) -> dict[str, bool]:
    adapter = get_provider_adapter(interaction_adapter_code(provider_code, account_type))
    return adapter.interaction_capabilities(
        {
            "provider_code": provider_code,
            "account_type": account_type,
        }
    )
