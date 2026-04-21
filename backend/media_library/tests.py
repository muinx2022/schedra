from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Workspace
from back_office.models import MediaUploadSettings

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


class MediaLibraryUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner2",
            email="owner2@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Demo 2", slug="demo-2", owner=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_upload_endpoint_stores_files_locally_even_if_cloudinary_is_selected(self):
        media_settings = MediaUploadSettings.load()
        media_settings.upload_provider = MediaUploadSettings.Provider.CLOUDINARY
        media_settings.cloudinary_cloud_name = "demo-cloud"
        media_settings.cloudinary_api_key = "demo-key"
        media_settings.cloudinary_api_secret_enc = "kept-as-is"
        media_settings.save()

        upload = BytesIO(b"fake-image-bytes")
        upload.name = "poster.jpg"

        response = self.client.post(
            "/api/media/",
            {"file": upload, "title": "Poster"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        asset = MediaAsset.objects.get(pk=response.data["id"])
        self.assertEqual(asset.storage_backend, "local")
        self.assertTrue(asset.storage_key.startswith("media_assets/"))

    def test_upload_endpoint_rejects_svg_disguised_as_png(self):
        upload = BytesIO(b'<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg"></svg>')
        upload.name = "logo.png"

        response = self.client.post(
            "/api/media/",
            {"file": upload, "title": "Logo"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "SVG uploads are not supported for social publishing. Export this asset as PNG or JPG first.",
        )

    @override_settings(APP_PUBLIC_BASE_URL="https://schedra.net", MEDIA_URL="/media/")
    def test_local_public_url_falls_back_to_app_public_base_url(self):
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
            "https://schedra.net/media/media_assets/local.jpg",
        )
