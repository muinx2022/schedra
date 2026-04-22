from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from accounts.models import Workspace
from social.models import SocialConnection, SocialProvider


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
            {"redirect_uri": "https://schedra.net/app/settings/provider/pinterest"},
            format="json",
        )
        self.assertEqual(start_response.status_code, 200)
        self.assertIn("authorize_url", start_response.data)
        self.assertTrue(start_response.data["state"])

        callback_response = self.client.post(
            "/api/connections/pinterest/callback/",
            {
                "code": "oauth-code",
                "redirect_uri": "https://schedra.net/app/settings/provider/pinterest",
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
