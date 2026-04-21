from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Workspace
from ideas.models import Idea
from publishing.models import Post, PostTarget
from social.models import QueueSlot, SocialAccount, SocialConnection


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

        self._purge_seeded_social_data(workspace)

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
        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Login: demo@example.com / demo12345")

    def _purge_seeded_social_data(self, workspace: Workspace) -> None:
        seeded_accounts = SocialAccount.objects.filter(workspace=workspace, metadata__seeded=True)
        if seeded_accounts.exists():
            QueueSlot.objects.filter(social_account__in=seeded_accounts).delete()
            PostTarget.objects.filter(social_account__in=seeded_accounts).delete()
            seeded_accounts.delete()

        SocialConnection.objects.filter(workspace=workspace, metadata__seeded=True).delete()
