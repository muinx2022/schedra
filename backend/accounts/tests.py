from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.test import APITestCase

from accounts.models import Workspace


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AuthFlowTests(APITestCase):
    def test_register_creates_single_workspace(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "owner@example.com",
                "password": "pass12345",
                "full_name": "Owner Test",
                "workspace_name": "My Workspace",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Workspace.objects.count(), 1)
        self.assertEqual(response.data["workspace"]["name"], "My Workspace")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome", mail.outbox[0].subject)

    def test_password_reset_request_sends_email_and_confirm_updates_password(self):
        user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="oldpass12345",
            first_name="Owner",
        )

        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "owner@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your", mail.outbox[0].subject)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        body = mail.outbox[0].body
        token = body.split("token=")[1].splitlines()[0].strip()

        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "password": "newpass12345",
            },
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 200)

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "owner@example.com", "password": "newpass12345"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

    def test_password_reset_request_does_not_leak_unknown_email(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "missing@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
