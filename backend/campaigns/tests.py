from io import BytesIO
import importlib.util
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Workspace
from campaigns.models import Campaign, CampaignMediaType, CampaignSegment
from media_library.models import MediaAsset
from publishing.models import Post, PostMedia


HAS_PYTHON_DOCX = importlib.util.find_spec("docx") is not None


def build_minimal_docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Intro</w:t></w:r></w:p>
    <w:p><w:r><w:t>##SEGMENT</w:t></w:r></w:p>
    <w:p><w:r><w:t>Segment one</w:t></w:r></w:p>
  </w:body>
</w:document>""",
        )
    return buffer.getvalue()


class CampaignFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="campaign-owner",
            email="campaign-owner@example.com",
            password="pass12345",
        )
        self.workspace = Workspace.objects.create(name="Campaign Demo", slug="campaign-demo", owner=self.user)
        self.client.force_authenticate(self.user)
        self.video_asset = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Source video",
            file="media_assets/source.mp4",
            storage_backend="local",
            storage_key="media_assets/source.mp4",
            file_name="source.mp4",
            content_type="video/mp4",
            size_bytes=2048,
        )
        self.image_asset_1 = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Image one",
            file="media_assets/one.jpg",
            storage_backend="local",
            storage_key="media_assets/one.jpg",
            file_name="one.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )
        self.image_asset_2 = MediaAsset.objects.create(
            workspace=self.workspace,
            uploaded_by=self.user,
            title="Image two",
            file="media_assets/two.jpg",
            storage_backend="local",
            storage_key="media_assets/two.jpg",
            file_name="two.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )

    def create_campaign(self, source_file=None, media_type="video", source_video=None, source_images=None):
        source_file = source_file or SimpleUploadedFile(
            "segments.txt",
            b"Intro\n##SEGMENT\nFirst segment\n##SEGMENT\nSecond segment\n",
            content_type="text/plain",
        )
        payload = {
            "title": "Launch campaign",
            "source_media_type": media_type,
            "source_file": source_file,
        }
        if source_video is None:
            source_video = self.video_asset if media_type == "video" else None
        if source_video is not None:
            payload["source_video"] = str(source_video.id)
        for image in source_images or []:
            payload.setdefault("source_images", []).append(str(image.id))
        response = self.client.post(
            "/api/campaigns/",
            payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_create_campaign_with_valid_txt_source(self):
        response = self.create_campaign()
        self.assertEqual(response.data["title"], "Launch campaign")
        self.assertEqual(response.data["source_file_type"], "txt")
        self.assertEqual(response.data["status"], "uploaded")
        self.assertEqual(response.data["source_media_type"], CampaignMediaType.VIDEO)

    @override_settings(APP_PUBLIC_BASE_URL="https://schedra.net")
    def test_campaign_source_file_url_uses_app_public_base_url(self):
        response = self.create_campaign()
        self.assertTrue(response.data["source_file_url"].startswith("https://schedra.net/"))

    @patch("campaigns.views.get_video_duration_seconds", return_value=11)
    def test_generate_segments_from_source_file(self, mocked_duration):
        create_response = self.create_campaign()

        response = self.client.post(f"/api/campaigns/{create_response.data['id']}/generate/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["segment_count"], 3)
        self.assertEqual(response.data["status"], "generated")
        self.assertEqual(response.data["total_video_duration_seconds"], 11)
        self.assertEqual(len(response.data["segments"]), 3)
        self.assertEqual(response.data["segments"][0]["start_seconds"], 0)
        self.assertEqual(response.data["segments"][0]["end_seconds"], 3)
        self.assertEqual(response.data["segments"][1]["start_seconds"], 3)
        self.assertEqual(response.data["segments"][1]["end_seconds"], 6)
        self.assertEqual(response.data["segments"][2]["start_seconds"], 6)
        self.assertEqual(response.data["segments"][2]["end_seconds"], 11)
        mocked_duration.assert_called_once()

    @patch("campaigns.views.get_video_duration_seconds", return_value=10)
    def test_generate_fails_when_segment_delimiter_missing(self, mocked_duration):
        create_response = self.create_campaign(
            SimpleUploadedFile("plain.txt", b"This file has no delimiter.", content_type="text/plain")
        )

        response = self.client.post(f"/api/campaigns/{create_response.data['id']}/generate/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("##SEGMENT", response.data["detail"])
        self.assertEqual(Campaign.objects.get(id=create_response.data["id"]).status, "failed")
        mocked_duration.assert_not_called()

    @patch("campaigns.views.get_video_duration_seconds", return_value=9)
    def test_generate_fails_when_docx_cannot_be_extracted(self, mocked_duration):
        create_response = self.create_campaign(
            SimpleUploadedFile(
                "broken.docx",
                b"not-a-real-docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        )

        response = self.client.post(f"/api/campaigns/{create_response.data['id']}/generate/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            "extract text" in response.data["detail"].lower()
            or "python-docx" in response.data["detail"].lower()
        )
        mocked_duration.assert_not_called()

    @patch("campaigns.views.get_video_duration_seconds", return_value=10)
    def test_create_drafts_creates_posts_with_clip_metadata_and_is_idempotent(self, mocked_duration):
        create_response = self.create_campaign()
        campaign_id = create_response.data["id"]

        generate_response = self.client.post(f"/api/campaigns/{campaign_id}/generate/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)

        first_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(first_response.status_code, 200, first_response.data)
        self.assertEqual(first_response.data["created_count"], 3)
        self.assertEqual(first_response.data["draft_count"], 3)
        self.assertEqual(Post.objects.count(), 3)

        segment = CampaignSegment.objects.get(campaign_id=campaign_id, order_index=0)
        self.assertIsNotNone(segment.draft_post_id)
        media_item = PostMedia.objects.get(post=segment.draft_post)
        self.assertEqual(media_item.metadata["clip_start_seconds"], 0)
        self.assertEqual(media_item.metadata["clip_end_seconds"], 3)
        self.assertEqual(media_item.metadata["clip_duration_seconds"], 3)
        self.assertEqual(media_item.metadata["source_campaign_id"], campaign_id)
        self.assertEqual(media_item.kind, "video")

        second_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(second_response.status_code, 200, second_response.data)
        self.assertEqual(second_response.data["created_count"], 0)
        self.assertEqual(Post.objects.count(), 3)
        mocked_duration.assert_called_once()

    @patch("campaigns.views.get_video_duration_seconds", return_value=13)
    def test_generate_supports_valid_docx_file(self, mocked_duration):
        if not HAS_PYTHON_DOCX:
            self.skipTest("python-docx is not installed in this interpreter")
        create_response = self.create_campaign(
            SimpleUploadedFile(
                "segments.docx",
                build_minimal_docx_bytes(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        )

        response = self.client.post(f"/api/campaigns/{create_response.data['id']}/generate/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["segment_count"], 2)
        self.assertEqual(response.data["segments"][1]["end_seconds"], 13)

    def test_create_campaign_without_media_is_allowed(self):
        response = self.create_campaign(media_type="none", source_video=None, source_images=[])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["source_media_type"], CampaignMediaType.NONE)

    def test_create_image_campaign_and_create_drafts(self):
        create_response = self.create_campaign(
            media_type="images",
            source_images=[self.image_asset_1, self.image_asset_2],
        )
        campaign_id = create_response.data["id"]

        generate_response = self.client.post(f"/api/campaigns/{campaign_id}/generate/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(generate_response.data["total_video_duration_seconds"], 0)
        self.assertEqual(generate_response.data["segments"][0]["start_seconds"], 0)

        first_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(first_response.status_code, 200, first_response.data)
        self.assertEqual(first_response.data["created_count"], 3)

        first_post_media = PostMedia.objects.filter(post__campaign_segments__campaign_id=campaign_id).order_by("created_at").first()
        self.assertEqual(first_post_media.kind, "image")
        self.assertEqual(first_post_media.media_asset_id, self.image_asset_1.id)

    def test_create_drafts_without_media_creates_text_only_posts(self):
        create_response = self.create_campaign(media_type="none", source_video=None, source_images=[])
        campaign_id = create_response.data["id"]

        generate_response = self.client.post(f"/api/campaigns/{campaign_id}/generate/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)

        draft_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(draft_response.status_code, 200, draft_response.data)
        self.assertEqual(draft_response.data["created_count"], 3)
        self.assertEqual(PostMedia.objects.count(), 0)

    def test_create_drafts_for_image_campaign_allows_missing_images_for_later_segments(self):
        create_response = self.create_campaign(media_type="images", source_images=[self.image_asset_1])
        campaign_id = create_response.data["id"]
        generate_response = self.client.post(f"/api/campaigns/{campaign_id}/generate/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)

        draft_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(draft_response.status_code, 200, draft_response.data)
        self.assertEqual(draft_response.data["created_count"], 3)
        self.assertEqual(Post.objects.count(), 3)

        media_items = list(PostMedia.objects.order_by("created_at"))
        self.assertEqual(len(media_items), 1)
        self.assertEqual(media_items[0].media_asset_id, self.image_asset_1.id)

    @patch("media_library.cleanup.get_backend_by_id")
    def test_delete_campaign_deletes_campaign_media_assets_from_storage(self, mocked_get_backend):
        backend = mocked_get_backend.return_value
        self.image_asset_1.storage_backend = "cloudinary"
        self.image_asset_1.storage_key = "campaign/image-one"
        self.image_asset_1.save(update_fields=["storage_backend", "storage_key"])
        self.image_asset_2.storage_backend = "cloudinary"
        self.image_asset_2.storage_key = "campaign/image-two"
        self.image_asset_2.save(update_fields=["storage_backend", "storage_key"])
        create_response = self.create_campaign(
            media_type="images",
            source_images=[self.image_asset_1, self.image_asset_2],
        )
        campaign_id = create_response.data["id"]
        generate_response = self.client.post(f"/api/campaigns/{campaign_id}/generate/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)
        draft_response = self.client.post(f"/api/campaigns/{campaign_id}/create-drafts/", {}, format="json")
        self.assertEqual(draft_response.status_code, 200, draft_response.data)

        delete_response = self.client.delete(f"/api/campaigns/{campaign_id}/")

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Campaign.objects.filter(id=campaign_id).exists())
        self.assertFalse(MediaAsset.objects.filter(id__in=[self.image_asset_1.id, self.image_asset_2.id]).exists())
        self.assertEqual(PostMedia.objects.count(), 0)
        backend.delete.assert_any_call("campaign/image-one", content_type="image/jpeg")
        backend.delete.assert_any_call("campaign/image-two", content_type="image/jpeg")
