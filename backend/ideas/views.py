from rest_framework import permissions, viewsets

from .models import Idea
from .serializers import IdeaSerializer


class IdeaViewSet(viewsets.ModelViewSet):
    serializer_class = IdeaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Idea.objects.filter(workspace=self.request.user.workspace).order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.user.workspace, author=self.request.user)

