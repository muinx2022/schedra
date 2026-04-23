from datetime import timedelta
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APITestCase

from accounts.models import Workspace
from back_office.models import MediaUploadSettings
from ideas.models import Idea
from media_library.models import MediaAsset
from social.models import SocialAccount, SocialConnection, SocialProvider
from social.views import ensure_default_queue_slots
from publishing.models import DeliveryStatus, Post, PostTarget
from publishing.tasks import dispatch_due_post_targets, poll_post_target_status


class PublishingFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Demo", slug="demo", owner=self.user)
        self.client.force_authenticate(self.user)
        self.facebook_provider = SocialProvider.objects.create(code="facebook", name="Facebook")
        self.instagram_provider = SocialProvider.objects.create(code="instagram", name="Instagram")
        self.connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=self.facebook_provider,
            status="connected",
            access_token="token",
        )
        self.instagram_connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=self.instagram_provider,
            status="connected",
            access_token="token",
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.connection,
            provider=self.facebook_provider,
            external_id="fb-page-1",
            display_name="Demo Page",
            account_type="page",
            metadata={"page_access_token": "token"},
        )
        self.instagram_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.instagram_connection,
            provider=self.instagram_provider,
            external_id="ig-business-1",
            display_name="demo_ig",
            account_type="instagram_business",
            metadata={"page_access_token": "token", "parent_page_id": "fb-page-1"},
        )
        ensure_default_queue_slots(self.account)
        ensure_default_queue_slots(self.instagram_account)
        self.asset1 = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="One",
            storage_backend="cloudinary",
            storage_key="demo/one",
            file_name="one.jpg",
            content_type="image/jpeg",
            size_bytes=123,
        )
        self.asset2 = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Two",
            storage_backend="cloudinary",
            storage_key="demo/two",
            file_name="two.jpg",
            content_type="image/jpeg",
            size_bytes=456,
        )
        MediaUploadSettings.load()

    def test_convert_idea_to_post(self):
        idea = Idea.objects.create(
            workspace=self.workspace,
            author=self.user,
            title="Launch teaser",
            note="Ship tomorrow",
        )
        response = self.client.post(f"/api/posts/from-idea/{idea.id}/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["internal_name"], "Launch teaser")

    def test_publish_now_marks_post_published(self):
        response = self.client.post(
            "/api/posts/",
            {
                "internal_name": "Hello",
                "caption_text": "Hello world",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "targets": [
                    {
                        "social_account": str(self.account.id),
                        "delivery_strategy": "now",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post_id = response.data["id"]
        publish_response = self.client.post(f"/api/posts/{post_id}/publish_now/", {}, format="json")
        self.assertEqual(publish_response.status_code, 200)
        refreshed = self.client.get(f"/api/posts/{post_id}/")
        self.assertEqual(refreshed.data["delivery_status"], "published")

    @patch("publishing.tasks.publish_post_target.delay")
    def test_publish_now_returns_immediately_after_queueing(self, mocked_publish_delay):
        response = self.client.post(
            "/api/posts/",
            {
                "internal_name": "Hello",
                "caption_text": "Hello world",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "targets": [
                    {
                        "social_account": str(self.account.id),
                        "delivery_strategy": "now",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(pk=response.data["id"])
        publish_response = self.client.post(f"/api/posts/{post.id}/publish_now/", {}, format="json")
        self.assertEqual(publish_response.status_code, 200)
        post.refresh_from_db()
        target = post.targets.get()
        self.assertEqual(post.delivery_status, DeliveryStatus.PUBLISHING)
        self.assertEqual(target.delivery_status, DeliveryStatus.PUBLISHING)
        mocked_publish_delay.assert_called_once_with(str(target.id))

    @patch("publishing.tasks.publish_post_target.delay")
    def test_publish_now_returns_503_without_flipping_status_when_queueing_fails(self, mocked_publish_delay):
        mocked_publish_delay.side_effect = RuntimeError("broker unavailable")
        response = self.client.post(
            "/api/posts/",
            {
                "internal_name": "Hello",
                "caption_text": "Hello world",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "targets": [
                    {
                        "social_account": str(self.account.id),
                        "delivery_strategy": "now",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(pk=response.data["id"])

        publish_response = self.client.post(f"/api/posts/{post.id}/publish_now/", {}, format="json")

        self.assertEqual(publish_response.status_code, 503)
        post.refresh_from_db()
        target = post.targets.get()
        self.assertEqual(post.delivery_status, DeliveryStatus.DRAFT)
        self.assertEqual(target.delivery_status, DeliveryStatus.DRAFT)
        self.assertIn("Could not queue publish task", publish_response.data["detail"])

    def test_instagram_single_post_requires_exactly_one_media(self):
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Instagram hello",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "single"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(self.asset1.id), "kind": "image", "role": "primary", "order_index": 0},
                    {"media_asset": str(self.asset2.id), "kind": "image", "role": "secondary", "order_index": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_instagram_carousel_requires_at_least_two_media(self):
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Instagram carousel",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "carousel"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(self.asset1.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_instagram_carousel_post_can_be_created(self):
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Instagram carousel",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "carousel"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(self.asset1.id), "kind": "image", "role": "primary", "order_index": 0},
                    {"media_asset": str(self.asset2.id), "kind": "image", "role": "secondary", "order_index": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    @patch("media_library.cleanup.get_backend_by_id")
    def test_delete_post_deletes_unreferenced_media_asset_from_storage(self, mocked_get_backend):
        backend = mocked_get_backend.return_value
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Draft with media",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "media_items": [
                    {"media_asset": str(self.asset1.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        delete_response = self.client.delete(f"/api/posts/{response.data['id']}/")

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Post.objects.filter(id=response.data["id"]).exists())
        self.assertFalse(MediaAsset.objects.filter(id=self.asset1.id).exists())
        backend.delete.assert_called_once_with("demo/one", content_type="image/jpeg")

    @patch("media_library.cleanup.get_backend_by_id")
    def test_delete_post_keeps_shared_media_asset(self, mocked_get_backend):
        first_response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "First",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "media_items": [
                    {"media_asset": str(self.asset2.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(first_response.status_code, 201, first_response.data)
        second_response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Second",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
                "media_items": [
                    {"media_asset": str(self.asset2.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(second_response.status_code, 201, second_response.data)

        delete_response = self.client.delete(f"/api/posts/{first_response.data['id']}/")

        self.assertEqual(delete_response.status_code, 204)
        self.assertTrue(MediaAsset.objects.filter(id=self.asset2.id).exists())
        mocked_get_backend.return_value.delete.assert_not_called()

    def test_media_asset_public_url_uses_local_public_base(self):
        media_settings = MediaUploadSettings.load()
        media_settings.local_public_base_url = "https://assets.example.com"
        media_settings.save()
        local_asset = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Local",
            file="media_assets/local.jpg",
            storage_backend="local",
            file_name="local.jpg",
            content_type="image/jpeg",
            size_bytes=789,
        )

        self.assertEqual(
            local_asset.get_public_file_url(),
            "https://assets.example.com/media/media_assets/local.jpg",
        )

    def test_media_upload_accepts_video_files(self):
        upload = SimpleUploadedFile(
            "clip.mp4",
            b"fake-video-bytes",
            content_type="video/mp4",
        )

        response = self.client.post(
            "/api/media/",
            {"file": upload, "title": "Clip"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], "video")
        self.assertEqual(response.data["content_type"], "video/mp4")

    def test_account_queue_slot_crud(self):
        create_response = self.client.post(
            f"/api/accounts/{self.account.id}/queue-slots/",
            {
                "weekday": 1,
                "local_time": "14:30:00",
                "is_active": True,
                "position": 9,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        slot_id = create_response.data["id"]

        update_response = self.client.patch(
            f"/api/accounts/{self.account.id}/queue-slots/{slot_id}/",
            {
                "is_active": False,
                "position": 2,
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["is_active"], False)
        self.assertEqual(update_response.data["position"], 2)

        delete_response = self.client.delete(f"/api/accounts/{self.account.id}/queue-slots/{slot_id}/")
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(self.account.queue_slots.filter(id=slot_id).exists())

    def test_account_queue_slot_rejects_duplicate_day_and_time(self):
        existing_slot = self.account.queue_slots.first()
        response = self.client.post(
            f"/api/accounts/{self.account.id}/queue-slots/",
            {
                "weekday": existing_slot.weekday,
                "local_time": existing_slot.local_time.strftime("%H:%M:%S"),
                "is_active": True,
                "position": 99,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.data["detail"])

    def test_publish_now_fails_for_local_media_without_public_base_url(self):
        local_asset = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Local",
            file="media_assets/local.jpg",
            storage_backend="local",
            file_name="local.jpg",
            content_type="image/jpeg",
            size_bytes=789,
        )
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Instagram hello",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "single"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(local_asset.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post_id = response.data["id"]

        publish_response = self.client.post(f"/api/posts/{post_id}/publish_now/", {}, format="json")
        self.assertEqual(publish_response.status_code, 400)
        self.assertIn("Local media assets need a public base URL", publish_response.data["detail"])

    def test_publish_now_uses_absolute_public_media_url(self):
        media_settings = MediaUploadSettings.load()
        media_settings.local_public_base_url = "https://assets.example.com"
        media_settings.save()
        local_asset = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Local",
            file="media_assets/local.jpg",
            storage_backend="local",
            file_name="local.jpg",
            content_type="image/jpeg",
            size_bytes=789,
        )
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Instagram hello",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "single"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(local_asset.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post_id = response.data["id"]

        with patch("publishing.tasks.get_provider_adapter") as mocked_get_provider_adapter:
            adapter = mocked_get_provider_adapter.return_value
            adapter.publish_post.return_value = {"provider_post_id": "ig-1", "status": "published"}

            publish_response = self.client.post(f"/api/posts/{post_id}/publish_now/", {}, format="json")

        self.assertEqual(publish_response.status_code, 200)
        request_payload = adapter.publish_post.call_args[0][1]
        self.assertEqual(
            request_payload["media_items"][0]["file_url"],
            "https://assets.example.com/media/media_assets/local.jpg",
        )

    @patch("publishing.tasks._schedule_publish_status_poll")
    @patch("publishing.tasks.get_provider_adapter")
    def test_tiktok_status_timeout_reschedules_poll_instead_of_failing(self, mocked_get_provider_adapter, mocked_schedule_poll):
        tiktok_provider = SocialProvider.objects.create(code="tiktok", name="TikTok")
        tiktok_connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=tiktok_provider,
            status="connected",
            access_token="token",
        )
        tiktok_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=tiktok_connection,
            provider=tiktok_provider,
            external_id="tt-creator-1",
            display_name="Demo TikTok",
            account_type="tiktok_creator",
            metadata={"access_token": "token"},
        )
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text="TikTok post",
            delivery_strategy="now",
            delivery_status=DeliveryStatus.PUBLISHING,
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=tiktok_account,
            delivery_strategy="now",
            delivery_status=DeliveryStatus.PUBLISHING,
            provider_result={"provider_post_id": "v_pub_url~v2-1.demo"},
        )

        adapter = mocked_get_provider_adapter.return_value
        adapter.get_publish_status.side_effect = ValueError(
            "Could not reach TikTok API from the local backend. timed out"
        )

        result = poll_post_target_status(str(target.id), attempts_left=4)

        self.assertEqual(result, {"status": "publishing", "attempts_left": 3})
        mocked_schedule_poll.assert_called_once_with(str(target.id), 3)
        target.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(target.delivery_status, DeliveryStatus.PUBLISHING)
        self.assertEqual(post.delivery_status, DeliveryStatus.PUBLISHING)

    @patch("publishing.tasks.get_provider_adapter")
    def test_final_poll_timeout_marks_post_failed(self, mocked_get_provider_adapter):
        tiktok_provider = SocialProvider.objects.create(code="tiktok_timeout", name="TikTok Timeout")
        tiktok_connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=tiktok_provider,
            status="connected",
            access_token="token",
        )
        tiktok_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=tiktok_connection,
            provider=tiktok_provider,
            external_id="tt-creator-timeout",
            display_name="Demo TikTok Timeout",
            account_type="tiktok_creator",
            metadata={"access_token": "token"},
        )
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text="TikTok timeout post",
            delivery_strategy="now",
            delivery_status=DeliveryStatus.PUBLISHING,
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=tiktok_account,
            delivery_strategy="now",
            delivery_status=DeliveryStatus.PUBLISHING,
            provider_result={"provider_post_id": "v_pub_url~timeout.demo", "status": "publishing"},
        )

        adapter = mocked_get_provider_adapter.return_value
        adapter.get_publish_status.return_value = {
            "provider_post_id": "v_pub_url~timeout.demo",
            "status": "publishing",
            "raw_status": "PROCESSING_PUBLISH",
        }

        result = poll_post_target_status(str(target.id), attempts_left=1)

        self.assertEqual(result["status"], "failed")
        self.assertIn("timed out", result["error"])
        target.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(target.delivery_status, DeliveryStatus.FAILED)
        self.assertEqual(post.delivery_status, DeliveryStatus.FAILED)
        self.assertIn("timed out", target.provider_result["error"])

    @patch("publishing.tasks.publish_post_target.delay")
    def test_dispatch_due_post_targets_keeps_scheduled_status_when_queueing_fails(self, mocked_publish_delay):
        mocked_publish_delay.side_effect = RuntimeError("broker unavailable")
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text="Scheduled post",
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=5),
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=self.account,
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=5),
        )

        result = dispatch_due_post_targets()

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["dispatch_errors"][0]["target_id"], str(target.id))
        target.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(target.delivery_status, DeliveryStatus.SCHEDULED)
        self.assertEqual(post.delivery_status, DeliveryStatus.SCHEDULED)

    def test_queue_assigns_next_scheduled_at_from_queue_slot(self):
        response = self.client.post(
            "/api/posts/",
            {
                "caption_text": "Queued post",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {"mode": "single"}},
                "targets": [
                    {
                        "social_account": str(self.instagram_account.id),
                        "delivery_strategy": "now",
                    }
                ],
                "media_items": [
                    {"media_asset": str(self.asset1.id), "kind": "image", "role": "primary", "order_index": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        queued = self.client.post(f"/api/posts/{response.data['id']}/queue/", {}, format="json")
        self.assertEqual(queued.status_code, 200)
        self.assertEqual(queued.data["post"]["delivery_status"], "queued")
        self.assertTrue(queued.data["post"]["scheduled_at"])

    def test_dispatch_due_post_targets_publishes_due_scheduled_targets(self):
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text="Scheduled post",
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=5),
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=self.account,
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=5),
        )

        with patch("publishing.tasks.get_provider_adapter") as mocked_get_provider_adapter:
            adapter = mocked_get_provider_adapter.return_value
            adapter.publish_post.return_value = {"provider_post_id": "fb-1", "status": "published"}

            result = dispatch_due_post_targets()

        self.assertEqual(result["count"], 1)
        target.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(target.delivery_status, DeliveryStatus.PUBLISHED)
        self.assertEqual(post.delivery_status, DeliveryStatus.PUBLISHED)

    def test_dispatch_due_post_targets_skips_future_targets(self):
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text="Future post",
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(hours=2),
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=self.account,
            delivery_strategy="schedule",
            delivery_status=DeliveryStatus.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(hours=2),
        )

        with patch("publishing.tasks.publish_post_target.delay") as mocked_delay:
            result = dispatch_due_post_targets()

        self.assertEqual(result["count"], 0)
        mocked_delay.assert_not_called()
        target.refresh_from_db()
        self.assertEqual(target.delivery_status, DeliveryStatus.SCHEDULED)
