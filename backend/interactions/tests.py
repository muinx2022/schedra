from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Workspace
from interactions.models import InteractionMessage, InteractionThread, InteractionTriageStatus
from interactions.services import sync_comments_for_account
from publishing.models import DeliveryStatus, Post, PostTarget
from social.models import SocialAccount, SocialConnection, SocialProvider


class InboxApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="inbox-owner",
            email="inbox@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(
            name="Inbox Demo",
            slug="inbox-demo",
            owner=self.user,
            timezone="Asia/Saigon",
        )
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

        self.facebook_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.facebook_connection,
            provider=self.facebook_provider,
            external_id="fb-page-1",
            display_name="Demo Facebook",
            account_type="page",
            metadata={"channel_code": "facebook", "page_access_token": "token"},
        )
        self.linkedin_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.linkedin_connection,
            provider=self.linkedin_provider,
            external_id="li-account-1",
            display_name="Demo LinkedIn",
            account_type="personal",
            metadata={"channel_code": "linkedin", "access_token": "token"},
        )

    def _create_post_target(self, account, *, status=DeliveryStatus.PUBLISHED, provider_post_id="provider-post-1"):
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text=f"{account.display_name} post",
            delivery_strategy="schedule",
            delivery_status=status,
            payload={"version": 1, "feed_post": {}},
        )
        return PostTarget.objects.create(
            post=post,
            social_account=account,
            delivery_strategy="schedule",
            delivery_status=status,
            provider_result={"provider_post_id": provider_post_id} if provider_post_id else {},
        )

    @patch("interactions.services.get_provider_adapter")
    def test_sync_ingests_only_app_published_targets_and_is_idempotent(self, get_adapter_mock):
        published_target = self._create_post_target(self.facebook_account, provider_post_id="fb-post-1")
        self._create_post_target(self.facebook_account, provider_post_id="")
        self._create_post_target(self.linkedin_account, provider_post_id="li-post-1")

        adapter = Mock()
        adapter.fetch_object_comments.return_value = {
            "comments": [
                {
                    "external_id": "comment-1",
                    "parent_external_id": "",
                    "author_name": "Alice",
                    "author_external_id": "alice-1",
                    "body_text": "Can you send details?",
                    "published_at": timezone.now() - timedelta(minutes=5),
                    "metadata": {},
                },
                {
                    "external_id": "comment-2",
                    "parent_external_id": "comment-1",
                    "author_name": "Alice",
                    "author_external_id": "alice-1",
                    "body_text": "Following up.",
                    "published_at": timezone.now() - timedelta(minutes=4),
                    "metadata": {},
                },
            ],
            "next_cursor": "cursor-2",
        }
        get_adapter_mock.return_value = adapter

        first = sync_comments_for_account(self.facebook_account)
        second = sync_comments_for_account(self.facebook_account)
        skipped = sync_comments_for_account(self.linkedin_account)

        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "success")
        self.assertEqual(skipped["status"], "skipped")
        self.assertEqual(InteractionThread.objects.count(), 1)
        self.assertEqual(InteractionMessage.objects.count(), 2)
        thread = InteractionThread.objects.get(post_target=published_target)
        self.assertEqual(thread.sync_cursor, "cursor-2")
        child = InteractionMessage.objects.get(external_id="comment-2")
        self.assertEqual(child.parent_message.external_id, "comment-1")

    @patch("interactions.services.get_provider_adapter")
    def test_thread_list_filters_and_triage_update(self, get_adapter_mock):
        target = self._create_post_target(self.facebook_account, provider_post_id="fb-post-2")
        adapter = Mock()
        adapter.fetch_object_comments.return_value = {
            "comments": [
                {
                    "external_id": "comment-3",
                    "parent_external_id": "",
                    "author_name": "Bob",
                    "author_external_id": "bob-1",
                    "body_text": "Interested",
                    "published_at": timezone.now(),
                    "metadata": {},
                }
            ],
            "next_cursor": "",
        }
        get_adapter_mock.return_value = adapter
        sync_comments_for_account(self.facebook_account)

        list_response = self.client.get("/api/inbox/threads/?platform=facebook")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["related_post_id"], str(target.post_id))

        thread_id = list_response.data[0]["id"]
        patch_response = self.client.patch(
            f"/api/inbox/threads/{thread_id}/",
            {"triage_status": InteractionTriageStatus.RESOLVED},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["triage_status"], InteractionTriageStatus.RESOLVED)

    @patch("interactions.views.sync_inbox_comments_workspace.delay")
    def test_sync_endpoint_queues_refresh(self, delay_mock):
        response = self.client.post(
            "/api/inbox/sync/",
            {"account": str(self.facebook_account.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        delay_mock.assert_called_once_with(str(self.workspace.id), str(self.facebook_account.id))
