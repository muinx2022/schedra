from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/update the default Back Office admin user."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin@local.test")
        parser.add_argument("--email", default="admin@local.test")
        parser.add_argument("--password", default="Admin@123")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        if not created and email:
            user.email = email

        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated user: {username}"))

