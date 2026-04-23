from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Workspace
from interactions.models import (
    InteractionDirection,
    InteractionMessage,
    InteractionThread,
    InteractionThreadType,
    InteractionTriageStatus,
)
from interactions.services import reply_to_thread_comment, sync_comments_for_account
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
        self.assertEqual(
            list_response.data[0]["interaction_capabilities"],
            {"inbox_comments": True, "reply_comments": True},
        )

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

    @patch("interactions.services.get_provider_adapter")
    def test_reply_endpoint_creates_outbound_message(self, get_adapter_mock):
        self._create_post_target(self.facebook_account, provider_post_id="fb-post-3")
        adapter = Mock()
        adapter.fetch_object_comments.return_value = {
            "comments": [
                {
                    "external_id": "comment-4",
                    "parent_external_id": "",
                    "author_name": "Carol",
                    "author_external_id": "carol-1",
                    "body_text": "Need pricing.",
                    "published_at": timezone.now() - timedelta(minutes=2),
                    "metadata": {},
                }
            ],
            "next_cursor": "",
        }
        adapter.reply_to_comment.return_value = {
            "external_id": "reply-1",
            "body_text": "Sent pricing in DM.",
            "published_at": timezone.now(),
            "metadata": {"provider": "facebook"},
        }
        get_adapter_mock.return_value = adapter
        sync_comments_for_account(self.facebook_account)

        thread = InteractionThread.objects.get(social_account=self.facebook_account)
        parent_message = InteractionMessage.objects.get(thread=thread, external_id="comment-4")
        response = self.client.post(
            f"/api/inbox/threads/{thread.id}/reply/",
            {
                "parent_message_id": str(parent_message.id),
                "body_text": " Sent pricing in DM. ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        thread.refresh_from_db()
        self.assertEqual(response.data["messages"][-1]["external_id"], "reply-1")
        reply = InteractionMessage.objects.get(thread=thread, external_id="reply-1")
        self.assertEqual(reply.parent_message_id, parent_message.id)
        self.assertEqual(reply.parent_external_id, parent_message.external_id)
        self.assertEqual(reply.direction, InteractionDirection.OUTBOUND)
        self.assertEqual(reply.body_text, "Sent pricing in DM.")
        self.assertEqual(thread.last_message_at, reply.published_at)
        self.assertEqual(response.data["messages"][-1]["direction"], InteractionDirection.OUTBOUND)

    @patch("interactions.services.get_provider_adapter")
    def test_reply_endpoint_rejects_invalid_targets_and_empty_body(self, get_adapter_mock):
        adapter = Mock()
        adapter.reply_to_comment.return_value = {
            "external_id": "reply-2",
            "body_text": "Acknowledged",
            "published_at": timezone.now(),
            "metadata": {},
        }
        get_adapter_mock.return_value = adapter
        first_thread = InteractionThread.objects.create(
            workspace=self.workspace,
            social_account=self.facebook_account,
            thread_type=InteractionThreadType.COMMENTS,
            external_object_id="fb-post-4",
        )
        second_thread = InteractionThread.objects.create(
            workspace=self.workspace,
            social_account=self.facebook_account,
            thread_type=InteractionThreadType.COMMENTS,
            external_object_id="fb-post-5",
        )
        first_message = InteractionMessage.objects.create(
            thread=first_thread,
            external_id="comment-5",
            parent_external_id="",
            author_name="Dana",
            author_external_id="dana-1",
            body_text="Question one",
            published_at=timezone.now() - timedelta(minutes=3),
        )
        second_message = InteractionMessage.objects.create(
            thread=second_thread,
            external_id="comment-6",
            parent_external_id="",
            author_name="Eli",
            author_external_id="eli-1",
            body_text="Question two",
            published_at=timezone.now() - timedelta(minutes=2),
        )

        empty_response = self.client.post(
            f"/api/inbox/threads/{first_thread.id}/reply/",
            {
                "parent_message_id": str(first_message.id),
                "body_text": "   ",
            },
            format="json",
        )
        self.assertEqual(empty_response.status_code, 400)
        self.assertIn("body_text", empty_response.data)

        wrong_thread_response = self.client.post(
            f"/api/inbox/threads/{first_thread.id}/reply/",
            {
                "parent_message_id": str(second_message.id),
                "body_text": "Still here",
            },
            format="json",
        )
        self.assertEqual(wrong_thread_response.status_code, 404)

        outbound = reply_to_thread_comment(
            thread=first_thread,
            parent_message=first_message,
            body_text="Acknowledged",
            user=self.user,
        )
        outbound_response = self.client.post(
            f"/api/inbox/threads/{first_thread.id}/reply/",
            {
                "parent_message_id": str(outbound.id),
                "body_text": "Second reply",
            },
            format="json",
        )
        self.assertEqual(outbound_response.status_code, 400)
        self.assertIn("parent_message_id", outbound_response.data)

    @patch("interactions.services.get_provider_adapter")
    def test_reply_endpoint_rejects_thread_without_reply_capability(self, get_adapter_mock):
        thread = InteractionThread.objects.create(
            workspace=self.workspace,
            social_account=self.linkedin_account,
            thread_type=InteractionThreadType.COMMENTS,
            external_object_id="li-post-1",
        )
        message = InteractionMessage.objects.create(
            thread=thread,
            external_id="li-comment-1",
            parent_external_id="",
            author_name="Frank",
            author_external_id="frank-1",
            body_text="Can you reply here?",
            published_at=timezone.now(),
        )

        response = self.client.post(
            f"/api/inbox/threads/{thread.id}/reply/",
            {
                "parent_message_id": str(message.id),
                "body_text": "Not supported",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Comment replies are not supported for this channel.")
        get_adapter_mock.assert_not_called()

    @patch("interactions.views.sync_inbox_comments_workspace.delay")
    def test_sync_endpoint_rejects_unsupported_account(self, delay_mock):
        response = self.client.post(
            "/api/inbox/sync/",
            {"account": str(self.linkedin_account.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Inbox sync is not supported for this channel.")
        delay_mock.assert_not_called()
