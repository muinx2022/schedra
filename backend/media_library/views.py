from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import MediaAsset
from .serializers import MediaAssetSerializer
from .storage import get_storage_backend


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

        backend = get_storage_backend()
        title = request.data.get("title") or file_obj.name

        if backend.backend_id == "local":
            # Delegate to Django's ImageField via serializer
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
        else:
            result = backend.upload(file_obj, file_obj.name, content_type)
            asset = MediaAsset.objects.create(
                workspace=request.user.workspace,
                uploaded_by=request.user,
                title=title,
                file_name=file_obj.name,
                content_type=content_type,
                size_bytes=file_obj.size,
                storage_backend=result.backend,
                storage_key=result.storage_key,
            )

        serializer = MediaAssetSerializer(asset, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
