from django.conf import settings
from django.db import models

from common.models import BaseModel


class Workspace(BaseModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace",
    )
    timezone = models.CharField(max_length=64, default="Asia/Saigon")

    def __str__(self) -> str:
        return self.name

