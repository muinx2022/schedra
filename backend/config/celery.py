import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("buffer_lite")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "dispatch-due-post-targets-every-minute": {
        "task": "publishing.tasks.dispatch_due_post_targets",
        "schedule": crontab(minute="*"),
    },
    "sync-provider-insights-hourly": {
        "task": "analytics.tasks.sync_provider_insights_batch",
        "schedule": crontab(minute="0"),
    },
    "sync-inbox-comments-every-5-minutes": {
        "task": "interactions.tasks.sync_inbox_comments_batch",
        "schedule": crontab(minute="*/5"),
    },
}
