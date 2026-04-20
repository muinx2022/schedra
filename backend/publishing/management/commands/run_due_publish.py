from django.core.management.base import BaseCommand

from publishing.tasks import dispatch_due_post_targets


class Command(BaseCommand):
    help = "Dispatch queued and scheduled post targets that are due for publishing."

    def handle(self, *args, **options):
        payload = dispatch_due_post_targets()
        count = (payload or {}).get("count", 0)
        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} due post target(s)."))
