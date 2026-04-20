from django.conf import settings
from django.db import models

from accounts.models import Workspace
from common.models import BaseModel


class IdeaColumn(models.TextChoices):
    UNASSIGNED = "unassigned", "Unassigned"
    TODO = "todo", "Todo"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"


class Idea(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="ideas")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ideas")
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True)
    column = models.CharField(max_length=32, choices=IdeaColumn.choices, default=IdeaColumn.UNASSIGNED)
    tags = models.JSONField(default=list, blank=True)
    image_urls = models.JSONField(default=list, blank=True)
