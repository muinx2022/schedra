from rest_framework.test import APITestCase

from accounts.models import Workspace


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

