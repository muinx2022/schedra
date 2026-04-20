from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

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
        "business_management",
        "read_insights",
        "pages_read_user_content",
        "instagram_basic",
        "instagram_manage_insights",
        "instagram_manage_comments",
    }

    @property
    def scopes(self) -> list[str]:
        raw = self.settings.meta_scopes or (
            "pages_show_list,business_management,pages_manage_posts,pages_read_engagement,pages_manage_metadata,"
            "pages_read_user_content,read_insights,instagram_basic,instagram_content_publish,"
            "instagram_manage_insights,instagram_manage_comments"
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
                ("impressions", "impressions"),
                ("reach", "reach"),
                ("engagement", "total_interactions"),
            ]
        else:
            metrics = [
                ("impressions", "page_impressions"),
                ("reach", "page_reach"),
                ("engagement", "page_post_engagements"),
            ]

        aggregated = {}
        for normalized_key, metric_name in metrics:
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
            data = payload.get("data", []) or []
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
                    "id,text,from{id,name},username,timestamp,parent{id},"
                    "replies{id,text,from{id,name},username,timestamp,parent{id}}"
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

        comments.sort(key=lambda item: item["published_at"])
        return {"comments": comments, "next_cursor": after or ""}

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
            "body_text": item.get("text", ""),
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

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthExchangeResult:
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
            # Single image — use /photos endpoint
            response = self._request(
                f"/{page_id}/photos",
                method="POST",
                data={
                    "url": media_items[0]["file_url"],
                    "message": caption,
                    "access_token": access_token,
                },
            )
        elif len(media_items) > 1:
            # Multiple images — upload each as unpublished, then attach to feed post
            media_ids = []
            for item in media_items:
                photo = self._request(
                    f"/{page_id}/photos",
                    method="POST",
                    data={
                        "url": item["file_url"],
                        "published": "false",
                        "access_token": access_token,
                    },
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

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthExchangeResult:
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
        raw = self.settings.linkedin_scopes or "openid,profile,email,w_member_social"
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
        headers_extra: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
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

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthExchangeResult:
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
        return [{
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

    def validate_credentials(self, access_token: str) -> dict[str, Any]:
        try:
            token = decrypt_value(access_token)
            profile = self._api("/userinfo", token)
            return {"valid": bool(profile.get("sub") or profile.get("id")), "provider": "linkedin"}
        except Exception as exc:
            return {"valid": False, "provider": "linkedin", "detail": str(exc)}

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        access_token = decrypt_value(target_account.get("access_token", ""))
        author_urn = f"urn:li:person:{target_account['external_id']}"
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        if media_items:
            # Upload each image then attach
            image_urns = [self._upload_image(access_token, item["file_url"]) for item in media_items]
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

    def _upload_image(self, access_token: str, file_url: str) -> str:
        # Step 1: Register upload
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": "urn:li:person:me",
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
        with urlopen(file_url) as img_response:
            image_data = img_response.read()

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

    def _api(
        self,
        path: str,
        access_token: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=UTF-8"
        request = Request(url, data=payload, method=method, headers=headers)
        try:
            with urlopen(request) as response:
                body = response.read().decode("utf-8")
                result = json.loads(body) if body else {}
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
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
            },
        )
        try:
            with urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ValueError(self._http_error_message(exc)) from exc
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
        result = self._api(
            "/user/info/",
            token,
            params={"fields": "open_id,union_id,display_name,avatar_url,profile_deep_link"},
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

    def publish_post(self, target_account: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        access_token = decrypt_value(target_account.get("access_token", ""))
        caption = payload.get("caption_text", "")
        media_items = payload.get("media_items") or []

        videos = [m for m in media_items if m.get("kind") == "video"]
        images = [m for m in media_items if m.get("kind") != "video"]

        if videos:
            return self._publish_video(access_token, caption, videos[0]["file_url"])
        elif images:
            return self._publish_photos(access_token, caption, [m["file_url"] for m in images])
        else:
            raise ValueError("TikTok requires at least one image or video.")

    def _publish_photos(self, access_token: str, caption: str, image_urls: list[str]) -> dict[str, Any]:
        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
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
        return {"provider_post_id": publish_id, "status": "published", "raw": result}

    def _publish_video(self, access_token: str, caption: str, video_url: str) -> dict[str, Any]:
        body = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
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
        return {"provider_post_id": publish_id, "status": "published", "raw": result}


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
    TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
    API_BASE = "https://api.pinterest.com/v5"

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
    def scopes(self) -> list[str]:
        raw = self.settings.pinterest_scopes or "boards:read,pins:read,pins:write"
        return [s.strip() for s in raw.split(",") if s.strip()]

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
            self.TOKEN_URL,
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

    def _api(self, path: str, access_token: str, method: str = "GET", data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.API_BASE}{path}"
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
        url = f"{self.API_BASE}/boards?page_size=50"
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

        result = self._api("/pins", access_token, method="POST", data=pin_data)
        return {
            "provider_post_id": result.get("id"),
            "status": "published",
            "url": result.get("link", ""),
            "raw": result,
        }

    def _upload_video(self, access_token: str, video_url: str) -> str:
        # Step 1: Register upload
        reg = self._api("/media", access_token, method="POST", data={"media_type": "video"})
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
            status_data = self._api(f"/media/{media_id}", access_token)
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
