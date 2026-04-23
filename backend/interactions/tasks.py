from accounts.models import Workspace
from config.celery import app
from social.models import SocialAccount

from .services import account_supports_inbox_comments, sync_comments_for_account


@app.task
def sync_inbox_comments_workspace(workspace_id: str, account_id: str | None = None):
    workspace = Workspace.objects.get(pk=workspace_id)
    accounts = SocialAccount.objects.filter(workspace=workspace).select_related("provider", "connection")
    if account_id:
        accounts = accounts.filter(pk=account_id)
    results = [sync_comments_for_account(account) for account in accounts if account_supports_inbox_comments(account)]
    return {"count": len(results), "results": results}


@app.task
def sync_inbox_comments_batch():
    payload = []
    for workspace in Workspace.objects.all().only("id"):
        payload.append(sync_inbox_comments_workspace.delay(str(workspace.id)))
    return {"queued": len(payload)}
