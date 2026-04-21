from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import MediaAsset
from .serializers import MediaAssetSerializer
class MediaAssetViewSet(viewsets.ModelViewSet):
    serializer_class = MediaAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MediaAsset.objects.filter(workspace=self.request.user.workspace).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        content_type = getattr(file_obj, "content_type", "") or "application/octet-stream"
        if not (content_type.startswith("image/") or content_type.startswith("video/")):
            return Response({"detail": "Only image and video uploads are supported."}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get("title") or file_obj.name

        # Keep upload URLs on the app's own domain so provider pull URLs can use a verified prefix.
        asset = MediaAsset.objects.create(
            workspace=request.user.workspace,
            uploaded_by=request.user,
            file=file_obj,
            title=title,
            file_name=file_obj.name,
            content_type=content_type,
            size_bytes=file_obj.size,
            storage_backend="local",
            storage_key="",
        )
        asset.storage_key = asset.file.name
        asset.save(update_fields=["storage_key"])

        serializer = MediaAssetSerializer(asset, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
