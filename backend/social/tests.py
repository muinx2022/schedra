from unittest.mock import Mock, patch
from datetime import datetime

from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Workspace
from social.adapters import FacebookAdapter, LinkedInAdapter, PinterestAdapter
from social.models import SocialAccount, SocialConnection, SocialProvider


class PinterestConnectionFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Demo", slug="demo-social", owner=self.user)
        self.client.force_authenticate(self.user)

    @patch("social.views.get_provider_adapter")
    def test_pinterest_start_callback_and_connect_board(self, mocked_get_provider_adapter):
        adapter = mocked_get_provider_adapter.return_value
        adapter.prepare_start.return_value = (
            "https://www.pinterest.com/oauth/?client_id=test",
            {"mock": True},
        )
        adapter.exchange_code.return_value = type(
            "ExchangeResult",
            (),
            {
                "external_user_id": "pinterest-user-1",
                "access_token": "plain-access-token",
                "refresh_token": "plain-refresh-token",
                "scopes": ["boards:read", "pins:read", "pins:write"],
                "metadata": {"account_level": "business"},
            },
        )()
        adapter.list_accounts.return_value = [
            {
                "external_id": "board-1",
                "display_name": "Recipes",
                "account_type": "pinterest_board",
                "timezone": "Asia/Saigon",
                "metadata": {
                    "access_token": "plain-access-token",
                    "board_url": "https://www.pinterest.com/demo/recipes/",
                    "privacy": "PUBLIC",
                },
            }
        ]

        start_response = self.client.post(
            "/api/connections/pinterest/start/",
            {"redirect_uri": "https://schedra.net/oauth/pinterest/callback"},
            format="json",
        )
        self.assertEqual(start_response.status_code, 200)
        self.assertIn("authorize_url", start_response.data)
        self.assertTrue(start_response.data["state"])

        callback_response = self.client.post(
            "/api/connections/pinterest/callback/",
            {
                "code": "oauth-code",
                "state": start_response.data["state"],
                "redirect_uri": "https://schedra.net/oauth/pinterest/callback",
            },
            format="json",
        )
        self.assertEqual(callback_response.status_code, 200)
        self.assertEqual(len(callback_response.data["accounts"]), 1)
        self.assertEqual(callback_response.data["accounts"][0]["account_type"], "pinterest_board")
        self.assertEqual(callback_response.data["accounts"][0]["display_name"], "Recipes")

        provider = SocialProvider.objects.get(code="pinterest")
        connection = SocialConnection.objects.get(workspace=self.workspace, provider=provider)
        self.assertEqual(connection.status, "connected")
        self.assertEqual(connection.external_user_id, "pinterest-user-1")
        self.assertEqual(connection.scopes, ["boards:read", "pins:read", "pins:write"])

        connect_response = self.client.post(
            "/api/connections/pinterest/connect-account/",
            {"external_id": "board-1"},
            format="json",
        )
        self.assertEqual(connect_response.status_code, 201)
        self.assertEqual(connect_response.data["account_type"], "pinterest_board")
        self.assertEqual(connect_response.data["provider_code"], "pinterest")
        self.assertEqual(connect_response.data["display_name"], "Recipes")
        self.assertEqual(connect_response.data["channel_name"], "Pinterest")
        self.assertEqual(len(connect_response.data["queue_slots"]), 3)

    @patch("social.views.get_provider_adapter")
    def test_pinterest_callback_rejects_wrong_state(self, mocked_get_provider_adapter):
        adapter = mocked_get_provider_adapter.return_value
        adapter.prepare_start.return_value = (
            "https://www.pinterest.com/oauth/?client_id=test",
            {"mock": True},
        )

        start_response = self.client.post(
            "/api/connections/pinterest/start/",
            {"redirect_uri": "https://schedra.net/oauth/pinterest/callback"},
            format="json",
        )
        self.assertEqual(start_response.status_code, 200)

        callback_response = self.client.post(
            "/api/connections/pinterest/callback/",
            {
                "code": "oauth-code",
                "state": "wrong-state",
                "redirect_uri": "https://schedra.net/oauth/pinterest/callback",
            },
            format="json",
        )

        self.assertEqual(callback_response.status_code, 400)
        self.assertEqual(callback_response.data["detail"], "Invalid OAuth state.")
        adapter.exchange_code.assert_not_called()

    @patch("social.adapters.SocialProviderSettings.load")
    def test_pinterest_adapter_always_requests_required_publish_scopes(self, settings_mock):
        settings_mock.return_value = Mock(
            pinterest_app_id="app-id",
            pinterest_app_secret_enc="encrypted-secret",
            pinterest_scopes="boards:read,pins:read,pins:write",
        )

        self.assertEqual(
            PinterestAdapter().scopes,
            ["boards:read", "pins:read", "pins:write", "boards:write"],
        )


class SocialAccountCapabilityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="accounts-owner",
            email="accounts@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Demo", slug="demo-accounts", owner=self.user)
        self.client.force_authenticate(self.user)

        self.facebook_provider = SocialProvider.objects.create(code="facebook", name="Facebook")
        self.linkedin_provider = SocialProvider.objects.create(code="linkedin", name="LinkedIn")

        self.facebook_connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=self.facebook_provider,
            status="connected",
            access_token="token",
        )
        self.linkedin_connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=self.linkedin_provider,
            status="connected",
            access_token="token",
        )

        SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.facebook_connection,
            provider=self.facebook_provider,
            external_id="fb-page-1",
            display_name="Demo Facebook",
            account_type="page",
            metadata={"channel_code": "facebook"},
        )
        SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.linkedin_connection,
            provider=self.linkedin_provider,
            external_id="li-account-1",
            display_name="Demo LinkedIn",
            account_type="personal",
            metadata={"channel_code": "linkedin"},
        )
        SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.linkedin_connection,
            provider=self.linkedin_provider,
            external_id="li-page-1",
            display_name="Demo LinkedIn Page",
            account_type="organization",
            metadata={"channel_code": "linkedin"},
        )

    def test_accounts_api_exposes_interaction_capabilities(self):
        response = self.client.get("/api/accounts/")

        self.assertEqual(response.status_code, 200)
        by_external_id = {item["external_id"]: item for item in response.data}
        self.assertEqual(
            by_external_id["fb-page-1"]["interaction_capabilities"],
            {"inbox_comments": True, "reply_comments": True},
        )
        self.assertEqual(
            by_external_id["li-account-1"]["interaction_capabilities"],
            {"inbox_comments": False, "reply_comments": False},
        )
        self.assertEqual(by_external_id["li-account-1"]["channel_name"], "LinkedIn Profile")
        self.assertEqual(by_external_id["li-page-1"]["channel_name"], "LinkedIn Page")


class ConnectAccountSelectionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="connect-owner",
            email="connect@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Connect", slug="connect-social", owner=self.user)
        self.client.force_authenticate(self.user)

    @patch("social.views.get_provider_adapter")
    def test_connect_account_uses_account_type_to_select_linkedin_page(self, mocked_get_provider_adapter):
        provider = SocialProvider.objects.create(code="linkedin", name="LinkedIn")
        SocialConnection.objects.create(
            workspace=self.workspace,
            provider=provider,
            status="connected",
            access_token="token",
        )
        adapter = mocked_get_provider_adapter.return_value
        adapter.list_accounts.return_value = [
            {
                "external_id": "shared-id",
                "display_name": "Owner Name",
                "account_type": "personal",
                "timezone": "Asia/Saigon",
                "metadata": {"access_token": "linkedin-token", "channel_code": "linkedin"},
            },
            {
                "external_id": "shared-id",
                "display_name": "Schedra Page",
                "account_type": "organization",
                "timezone": "Asia/Saigon",
                "metadata": {
                    "access_token": "linkedin-token",
                    "channel_code": "linkedin",
                    "organization_urn": "urn:li:organization:shared-id",
                },
            },
        ]

        response = self.client.post(
            "/api/connections/linkedin/connect-account/",
            {"external_id": "shared-id", "account_type": "organization"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["display_name"], "Schedra Page")
        self.assertEqual(response.data["account_type"], "organization")
        self.assertEqual(response.data["channel_name"], "LinkedIn Page")


class LinkedInAdapterTests(APITestCase):
    @patch("social.adapters.decrypt_value", return_value="linkedin-token")
    @patch("social.adapters.SocialProviderSettings.load")
    def test_list_accounts_returns_profile_and_pages(self, settings_mock, _decrypt_mock):
        settings_mock.return_value = Mock(
            linkedin_client_id="client-id",
            linkedin_client_secret_enc="encrypted-secret",
            linkedin_scopes="openid,profile,email,w_member_social,w_organization_social,r_organization_admin",
        )
        adapter = LinkedInAdapter()

        def fake_api(path, access_token, method="GET", data=None, query=None, headers_extra=None):
            if path == "/userinfo":
                return {"sub": "person-1", "name": "Owner Name", "email": "owner@example.com", "picture": "https://img"}
            if path == "/organizationAcls":
                return {
                    "elements": [
                        {"role": "ADMINISTRATOR", "organization": "urn:li:organization:123"},
                        {"role": "ANALYST", "organization": "urn:li:organization:999"},
                    ]
                }
            if path == "/organizations/123":
                return {"localizedName": "Schedra Page", "vanityName": "schedra"}
            raise AssertionError(f"Unexpected path: {path}")

        adapter._api = fake_api

        accounts = adapter.list_accounts("encrypted-token")

        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]["account_type"], "personal")
        self.assertEqual(accounts[1]["account_type"], "organization")
        self.assertEqual(accounts[1]["display_name"], "Schedra Page")
        self.assertEqual(accounts[1]["metadata"]["organization_urn"], "urn:li:organization:123")

    @patch("social.adapters.decrypt_value", return_value="linkedin-token")
    @patch("social.adapters.SocialProviderSettings.load")
    def test_publish_post_uses_organization_urn_for_linkedin_pages(self, settings_mock, _decrypt_mock):
        settings_mock.return_value = Mock(
            linkedin_client_id="client-id",
            linkedin_client_secret_enc="encrypted-secret",
            linkedin_scopes="openid,profile,email,w_member_social,w_organization_social,r_organization_admin",
        )
        adapter = LinkedInAdapter()
        captured = {}

        def fake_api(path, access_token, method="GET", data=None, query=None, headers_extra=None):
            captured["path"] = path
            captured["data"] = data
            return {"id": "urn:li:share:1"}

        adapter._api = fake_api

        result = adapter.publish_post(
            {
                "external_id": "123",
                "account_type": "organization",
                "access_token": "encrypted-token",
                "organization_urn": "urn:li:organization:123",
            },
            {"caption_text": "Hello page", "media_items": []},
        )

        self.assertEqual(result["status"], "published")
        self.assertEqual(captured["path"], "/ugcPosts")
        self.assertEqual(captured["data"]["author"], "urn:li:organization:123")


class MetaCommentNormalizationTests(APITestCase):
    def test_normalize_meta_comment_uses_facebook_message_field(self):
        adapter = FacebookAdapter()

        comment = adapter._normalize_meta_comment(
            {
                "id": "comment-1",
                "message": "This is the real Facebook comment",
                "from": {"id": "user-1", "name": "User One"},
                "timestamp": "2026-04-24T09:30:00+0000",
            }
        )

        self.assertEqual(comment["body_text"], "This is the real Facebook comment")


class FacebookPublishingFallbackTests(APITestCase):
    @override_settings(SOCIAL_FORCE_MOCK=False)
    @patch("social.adapters.decrypt_value", return_value="page-token")
    @patch("social.adapters.SocialProviderSettings.load")
    def test_publish_post_falls_back_to_direct_binary_upload_when_image_url_is_rejected(self, settings_mock, _decrypt_mock):
        settings_mock.return_value = Mock(
            meta_graph_base_url="https://graph.facebook.com/v23.0",
            meta_auth_base_url="https://www.facebook.com/v23.0/dialog/oauth",
            meta_app_id="app-id",
            meta_app_secret_enc="encrypted-secret",
            meta_scopes="pages_show_list,pages_manage_posts",
        )
        adapter = FacebookAdapter()

        def fake_request(path, query=None, method="GET", data=None):
            if path == "/page-1/photos" and method == "POST":
                raise ValueError("Missing or invalid image file (OAuthException 324)")
            raise AssertionError(f"Unexpected request: {path} {method}")

        adapter._request = fake_request
        adapter.fetch_media_bytes = Mock(return_value=(b"image-bytes", "image/jpeg"))
        adapter._request_multipart = Mock(return_value={"id": "fb-photo-1"})

        result = adapter.publish_post(
            {"external_id": "page-1", "page_access_token": "encrypted-token"},
            {
                "caption_text": "Hello world",
                "media_items": [{"id": "media-1", "file_url": "https://socialman.com/media/demo.jpg"}],
            },
        )

        self.assertEqual(result["status"], "published")
        self.assertEqual(result["provider_post_id"], "fb-photo-1")
        adapter._request_multipart.assert_called_once_with(
            "/page-1/photos",
            fields={"access_token": "page-token", "message": "Hello world"},
            files={"source": ("upload", b"image-bytes", "image/jpeg")},
        )

    def test_fetch_media_bytes_falls_back_to_local_asset_when_remote_fetch_fails(self):
        adapter = FacebookAdapter()
        adapter.fetch_remote_media_bytes = Mock(side_effect=ValueError("ssl verify failed"))
        adapter._load_local_media_asset_bytes = Mock(return_value=(b"local-bytes", "image/png"))

        content, content_type = adapter.fetch_media_bytes(
            {"id": "media-1", "file_url": "https://socialman.com/media/demo.png"}
        )

        self.assertEqual(content, b"local-bytes")
        self.assertEqual(content_type, "image/png")
        adapter._load_local_media_asset_bytes.assert_called_once_with("media-1")


class MetaInsightsFallbackTests(APITestCase):
    @override_settings(SOCIAL_FORCE_MOCK=False)
    @patch("social.adapters.decrypt_value", return_value="app-secret")
    @patch("social.adapters.SocialProviderSettings.load")
    def test_fetch_daily_insights_falls_back_when_primary_metric_is_invalid(self, settings_mock, _decrypt_mock):
        settings_mock.return_value = Mock(
            meta_graph_base_url="https://graph.facebook.com/v23.0",
            meta_auth_base_url="https://www.facebook.com/v23.0/dialog/oauth",
            meta_app_id="app-id",
            meta_app_secret_enc="encrypted-secret",
            meta_scopes="pages_show_list,pages_read_engagement",
        )
        adapter = FacebookAdapter()

        def fake_request(path, query=None, method="GET", data=None):
            metric = (query or {}).get("metric")
            if metric == "views":
                raise ValueError("(#100) The value must be a valid insights metric (OAuthException 100)")
            return {
                "data": [
                    {
                        "values": [
                            {
                                "end_time": "2026-04-24T07:00:00+0000",
                                "value": 12,
                            }
                        ]
                    }
                ]
            }

        adapter._request = fake_request

        rows = adapter.fetch_daily_insights(
            {"external_id": "page-1", "page_access_token": "token", "account_type": "page"},
            since_date=datetime(2026, 4, 24).date(),
            until_date=datetime(2026, 4, 24).date(),
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["impressions"], 12)
