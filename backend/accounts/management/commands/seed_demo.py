import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Workspace
from common.security import encrypt_value
from ideas.models import Idea
from publishing.models import Post, PostTarget
from social.models import QueueSlot, SocialAccount, SocialConnection, SocialProvider


class Command(BaseCommand):
    help = "Seed a demo workspace, user, social connections, ideas, and posts."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@example.com",
                "first_name": "Demo",
                "last_name": "User",
            },
        )
        user.set_password("demo12345")
        user.save()

        workspace, _ = Workspace.objects.get_or_create(
            owner=user,
            defaults={"name": "Demo Workspace", "slug": "demo-workspace"},
        )

        facebook_provider, _ = SocialProvider.objects.get_or_create(
            code="facebook",
            defaults={
                "name": "Facebook",
                "capabilities": {
                    "account_types": ["page"],
                    "content_types": ["feed_post"],
                    "images": True,
                },
            },
        )
        instagram_provider, _ = SocialProvider.objects.get_or_create(
            code="instagram",
            defaults={
                "name": "Instagram",
                "capabilities": {
                    "account_types": ["instagram_business"],
                    "content_types": ["feed_post", "carousel"],
                    "images": True,
                },
            },
        )

        # Skip mock social data when real Meta credentials are configured in staff settings.
        real_credentials = False
        if not real_credentials:
            facebook_connection, _ = SocialConnection.objects.get_or_create(
                workspace=workspace,
                provider=facebook_provider,
                defaults={
                    "external_user_id": "fb-demo-user",
                    "status": "connected",
                    "access_token": encrypt_value("demo-access-token"),
                    "scopes": ["pages_manage_posts", "pages_read_engagement"],
                    "metadata": {"seeded": True, "mock": True},
                },
            )
            instagram_connection, _ = SocialConnection.objects.get_or_create(
                workspace=workspace,
                provider=instagram_provider,
                defaults={
                    "external_user_id": "ig-demo-user",
                    "status": "connected",
                    "access_token": encrypt_value("demo-access-token"),
                    "scopes": ["instagram_basic", "instagram_content_publish"],
                    "metadata": {"seeded": True, "mock": True},
                },
            )
            account, _ = SocialAccount.objects.get_or_create(
                workspace=workspace,
                connection=facebook_connection,
                provider=facebook_provider,
                external_id="fb-page-1",
                defaults={
                    "account_type": "page",
                    "display_name": "Demo Facebook Page",
                    "timezone": "Asia/Saigon",
                    "metadata": {"page_access_token": encrypt_value("demo-page-token"), "seeded": True},
                },
            )
            SocialAccount.objects.get_or_create(
                workspace=workspace,
                connection=instagram_connection,
                provider=instagram_provider,
                external_id="ig-business-1",
                defaults={
                    "account_type": "instagram_business",
                    "display_name": "demo_instagram",
                    "timezone": "Asia/Saigon",
                    "metadata": {
                        "access_token": encrypt_value("demo-page-token"),
                        "page_access_token": encrypt_value("demo-page-token"),
                        "parent_page_id": "fb-page-1",
                        "username": "demo_instagram",
                        "seeded": True,
                    },
                },
            )
            for position, (weekday, local_time) in enumerate([(0, "09:00"), (2, "09:00"), (4, "09:00")]):
                QueueSlot.objects.get_or_create(
                    social_account=account,
                    weekday=weekday,
                    local_time=local_time,
                    defaults={"position": position},
                )

        idea, _ = Idea.objects.get_or_create(
            workspace=workspace,
            author=user,
            title="Seeded launch idea",
            defaults={
                "note": "Introduce the product and point people to the landing page.",
                "column": "planned",
                "tags": ["launch", "facebook"],
            },
        )

        post, _ = Post.objects.get_or_create(
            workspace=workspace,
            author=user,
            internal_name="Seeded welcome post",
            defaults={
                "source_idea": idea,
                "caption_text": "Buffer-lite is ready for testing.",
                "content_type": "feed_post",
                "editorial_state": "draft",
                "delivery_strategy": "now",
                "delivery_status": "draft",
                "payload": {"version": 1, "feed_post": {}},
            },
        )
        if not real_credentials:
            PostTarget.objects.get_or_create(
                post=post,
                social_account=account,
                defaults={"delivery_strategy": "now", "delivery_status": "draft"},
            )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Login: demo@example.com / demo12345")
