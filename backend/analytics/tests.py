from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from analytics.models import ProviderDailyInsight, ProviderMetricKey, ProviderSyncState, ProviderSyncStatus, ProviderSyncType
from analytics.tasks import sync_provider_insights_for_account
from accounts.models import Workspace
from publishing.models import DeliveryStatus, Post, PostTarget, PublishAttempt
from social.models import QueueSlot, SocialAccount, SocialConnection, SocialProvider


class AnalyticsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="analytics-owner",
            email="analytics@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(
            name="Analytics Demo",
            slug="analytics-demo",
            owner=self.user,
            timezone="Asia/Saigon",
        )
        self.client.force_authenticate(self.user)

        self.facebook_provider = SocialProvider.objects.create(code="facebook", name="Facebook")
        self.instagram_provider = SocialProvider.objects.create(code="instagram", name="Instagram")

        self.facebook_connection = SocialConnection.objects.create(
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

        self.facebook_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.facebook_connection,
            provider=self.facebook_provider,
            external_id="fb-page-1",
            display_name="Demo Facebook",
            account_type="page",
            metadata={"page_access_token": "token"},
        )
        self.instagram_account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.instagram_connection,
            provider=self.instagram_provider,
            external_id="ig-account-1",
            display_name="Demo Instagram",
            account_type="instagram_business",
            metadata={"page_access_token": "token"},
        )

        QueueSlot.objects.create(social_account=self.facebook_account, weekday=0, local_time="09:00", is_active=True, position=0)
        QueueSlot.objects.create(social_account=self.facebook_account, weekday=2, local_time="09:00", is_active=False, position=1)
        QueueSlot.objects.create(social_account=self.instagram_account, weekday=1, local_time="10:00", is_active=True, position=0)

    def _create_attempt(self, account, *, status, finished_at, error_detail=""):
        post = Post.objects.create(
            workspace=self.workspace,
            author=self.user,
            caption_text=f"{account.display_name} {status}",
            delivery_strategy="schedule",
            delivery_status=status,
            payload={"version": 1, "feed_post": {}},
        )
        target = PostTarget.objects.create(
            post=post,
            social_account=account,
            delivery_strategy="schedule",
            delivery_status=status,
        )
        return PublishAttempt.objects.create(
            post_target=target,
            status=status,
            request_payload={},
            response_payload={},
            error_detail=error_detail,
            finished_at=finished_at,
        )

    def test_zero_state_returns_empty_analytics_payload(self):
        response = self.client.get("/api/analytics/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "internal")
        self.assertEqual(response.data["summary"]["published_attempts"], 0)
        self.assertEqual(response.data["summary"]["failed_attempts"], 0)
        self.assertEqual(response.data["summary"]["success_rate"], 0)
        self.assertEqual(response.data["summary"]["connected_channels"], 2)
        self.assertEqual(response.data["summary"]["active_queue_slots"], 2)
        self.assertEqual(len(response.data["series"]), 30)
        self.assertEqual(response.data["recent_failures"], [])

    def test_summary_counts_and_success_rate_use_publish_attempts(self):
        now = timezone.now()
        self._create_attempt(self.facebook_account, status=DeliveryStatus.PUBLISHED, finished_at=now - timedelta(days=1))
        self._create_attempt(self.facebook_account, status=DeliveryStatus.FAILED, finished_at=now - timedelta(hours=5), error_detail="Rate limit")
        self._create_attempt(self.instagram_account, status=DeliveryStatus.PUBLISHED, finished_at=now - timedelta(hours=2))

        response = self.client.get("/api/analytics/?range=30d")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["published_attempts"], 2)
        self.assertEqual(response.data["summary"]["failed_attempts"], 1)
        self.assertEqual(response.data["summary"]["success_rate"], 67)
        self.assertEqual(response.data["channels"][0]["published_attempts"], 1)

    def test_range_filter_only_counts_attempts_inside_selected_window(self):
        now = timezone.now()
        self._create_attempt(self.facebook_account, status=DeliveryStatus.PUBLISHED, finished_at=now - timedelta(days=2))
        self._create_attempt(self.facebook_account, status=DeliveryStatus.PUBLISHED, finished_at=now - timedelta(days=40))

        response = self.client.get("/api/analytics/?range=7d")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["published_attempts"], 1)

    def test_account_filter_limits_summary_and_channels_to_one_account(self):
        now = timezone.now()
        self._create_attempt(self.facebook_account, status=DeliveryStatus.PUBLISHED, finished_at=now - timedelta(days=1))
        self._create_attempt(self.instagram_account, status=DeliveryStatus.FAILED, finished_at=now - timedelta(hours=1), error_detail="Bad media")

        response = self.client.get(f"/api/analytics/?range=30d&account={self.instagram_account.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["filters"]["account_id"], str(self.instagram_account.id))
        self.assertEqual(response.data["summary"]["connected_channels"], 1)
        self.assertEqual(response.data["summary"]["active_queue_slots"], 1)
        self.assertEqual(len(response.data["channels"]), 1)
        self.assertEqual(response.data["channels"][0]["account_id"], str(self.instagram_account.id))
        self.assertEqual(response.data["summary"]["failed_attempts"], 1)

    def test_series_buckets_attempts_using_workspace_timezone(self):
        finished_at = datetime(2026, 4, 19, 17, 30, tzinfo=dt_timezone.utc)
        self._create_attempt(self.facebook_account, status=DeliveryStatus.PUBLISHED, finished_at=finished_at)

        response = self.client.get("/api/analytics/?range=7d")

        self.assertEqual(response.status_code, 200)
        point = next(item for item in response.data["series"] if item["date"] == "2026-04-20")
        self.assertEqual(point["published_attempts"], 1)

    def test_recent_failures_are_sorted_descending(self):
        older = timezone.now() - timedelta(days=1)
        newer = timezone.now() - timedelta(hours=1)
        self._create_attempt(self.facebook_account, status=DeliveryStatus.FAILED, finished_at=older, error_detail="Older failure")
        self._create_attempt(self.instagram_account, status=DeliveryStatus.FAILED, finished_at=newer, error_detail="Newer failure")

        response = self.client.get("/api/analytics/?range=30d")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["recent_failures"]), 2)
        self.assertEqual(response.data["recent_failures"][0]["error_detail"], "Newer failure")
        self.assertEqual(response.data["recent_failures"][1]["error_detail"], "Older failure")

    def test_analytics_response_includes_provider_blocks(self):
        ProviderDailyInsight.objects.create(
            social_account=self.facebook_account,
            metric_date=timezone.localdate(),
            metric_key=ProviderMetricKey.IMPRESSIONS,
            value=120,
        )
        ProviderDailyInsight.objects.create(
            social_account=self.facebook_account,
            metric_date=timezone.localdate(),
            metric_key=ProviderMetricKey.REACH,
            value=90,
        )
        ProviderDailyInsight.objects.create(
            social_account=self.facebook_account,
            metric_date=timezone.localdate(),
            metric_key=ProviderMetricKey.ENGAGEMENT,
            value=18,
        )
        ProviderSyncState.objects.create(
            social_account=self.facebook_account,
            sync_type=ProviderSyncType.INSIGHTS,
            status=ProviderSyncStatus.SUCCESS,
            last_success_at=timezone.now() - timedelta(minutes=15),
        )

        response = self.client.get("/api/analytics/?range=7d")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider_summary"]["impressions"], 120)
        self.assertEqual(response.data["provider_summary"]["reach"], 90)
        self.assertEqual(response.data["provider_summary"]["engagement"], 18)
        self.assertEqual(len(response.data["provider_series"]), 7)
        self.assertEqual(response.data["provider_channels"][0]["sync_status"], ProviderSyncStatus.SUCCESS)

    @patch("analytics.views.sync_provider_insights_workspace.delay")
    def test_provider_sync_endpoint_queues_refresh(self, delay_mock):
        response = self.client.post(
            "/api/analytics/provider-sync/",
            {"account": str(self.facebook_account.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        delay_mock.assert_called_once_with(str(self.workspace.id), str(self.facebook_account.id))


class ProviderSyncTaskTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="provider-sync-owner",
            email="provider-sync@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(
            name="Provider Sync Demo",
            slug="provider-sync-demo",
            owner=self.user,
            timezone="Asia/Saigon",
        )
        self.provider = SocialProvider.objects.create(code="facebook", name="Facebook")
        self.connection = SocialConnection.objects.create(
            workspace=self.workspace,
            provider=self.provider,
            status="connected",
            access_token="token",
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            connection=self.connection,
            provider=self.provider,
            external_id="fb-page-1",
            display_name="Demo Facebook",
            account_type="page",
            metadata={"page_access_token": "token"},
        )

    @patch("analytics.tasks.get_provider_adapter")
    def test_first_sync_backfills_thirty_days_and_upserts_metrics(self, get_adapter_mock):
        adapter = Mock()
        adapter.fetch_daily_insights.return_value = [
            {"date": timezone.localdate(), "impressions": 100, "reach": 80, "engagement": 12}
        ]
        get_adapter_mock.return_value = adapter

        result = sync_provider_insights_for_account(self.account)

        self.assertEqual(result["status"], "success")
        args = adapter.fetch_daily_insights.call_args.args
        self.assertEqual((args[2] - args[1]).days, 29)
        self.assertEqual(
            ProviderDailyInsight.objects.filter(social_account=self.account).count(),
            3,
        )
        state = ProviderSyncState.objects.get(social_account=self.account, sync_type=ProviderSyncType.INSIGHTS)
        self.assertEqual(state.status, ProviderSyncStatus.SUCCESS)

    @patch("analytics.tasks.get_provider_adapter")
    def test_recurring_sync_refreshes_three_day_window(self, get_adapter_mock):
        ProviderSyncState.objects.create(
            social_account=self.account,
            sync_type=ProviderSyncType.INSIGHTS,
            status=ProviderSyncStatus.SUCCESS,
            last_success_at=timezone.now() - timedelta(hours=2),
        )
        adapter = Mock()
        adapter.fetch_daily_insights.return_value = []
        get_adapter_mock.return_value = adapter

        sync_provider_insights_for_account(self.account)

        args = adapter.fetch_daily_insights.call_args.args
        self.assertEqual((args[2] - args[1]).days, 2)
