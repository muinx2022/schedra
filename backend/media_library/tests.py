from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Workspace

from .models import MediaAsset
from .storage import CloudinaryBackend


class _FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MediaLibraryStorageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Demo", slug="demo", owner=self.user)

    @patch("media_library.storage.urlopen")
    def test_cloudinary_video_upload_uses_video_endpoint(self, mocked_urlopen):
        backend = CloudinaryBackend(
            cloud_name="demo-cloud",
            api_key="demo-key",
            api_secret="demo-secret",
        )
        mocked_urlopen.return_value = _FakeResponse(
            b'{"public_id":"videos/demo-clip","secure_url":"https://res.cloudinary.com/demo-cloud/video/upload/videos/demo-clip.mp4"}'
        )

        file_obj = BytesIO(b"fake-video-bytes")
        result = backend.upload(file_obj, "clip.mp4", "video/mp4")

        request = mocked_urlopen.call_args.args[0]
        self.assertIn("/video/upload", request.full_url)
        self.assertEqual(result.storage_key, "videos/demo-clip")
        self.assertEqual(result.url, "https://res.cloudinary.com/demo-cloud/video/upload/videos/demo-clip.mp4")

    def test_cloudinary_video_asset_uses_video_delivery_url(self):
        asset = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Clip",
            storage_backend="cloudinary",
            storage_key="videos/demo-clip",
            file_name="clip.mp4",
            content_type="video/mp4",
            size_bytes=123,
        )

        backend = CloudinaryBackend(
            cloud_name="demo-cloud",
            api_key="demo-key",
            api_secret="demo-secret",
        )
        with patch("media_library.storage._cloudinary_from_db_or_env", return_value=backend):
            self.assertEqual(
                asset.get_file_url(),
                "https://res.cloudinary.com/demo-cloud/video/upload/videos/demo-clip",
            )
