# Buffer Lite

Buffer-lite v1 built with `Django 6.x` and `Nuxt 4.x`.

## Included

- Public-facing Nuxt landing page
- Email/password auth with Django session
- Single-workspace app shell
- Ideas kanban with `Inbox`, `Planned`, `Ready`
- Facebook connection flow through a thin provider adapter
- Post draft / queue / schedule / publish-now flows
- Per-page queue slots
- Image-first media model
- Celery worker + Celery Beat scheduling for queued and scheduled publishing

## Facebook integration

The Facebook adapter now supports two modes:

# schedra

- `real Meta mode` when `META_APP_ID` and `META_APP_SECRET` are set
- `mock mode` when those env vars are missing

Real mode exchanges the OAuth code, lists manageable Pages, stores encrypted tokens, and publishes feed posts through the Graph API. Mock mode keeps the workspace flow testable locally without Meta credentials.

## Backend

```bash
cd backend
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000
```

For background publishing in production, run these alongside Django:

```bash
cd backend
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

## Frontend

```bash
cd frontend
npm run dev
```

The Nuxt BFF proxies requests to Django through `NUXT_BACKEND_BASE`, which defaults to `http://127.0.0.1:8000`.

## One command from root

From the project root on Windows:

```bash
dev.cmd
```

That command:

- creates `backend/.env` from `.env.example` if missing
- runs `migrate`
- runs `seed_demo`
- starts Django on `127.0.0.1:8000`
- starts a Celery worker
- starts Celery Beat with a 1-minute publish scan
- starts Nuxt on `127.0.0.1:3000`
- streams both services into the same terminal

You can also run it directly with:

```bash
python run_dev.py
```

## Seeded login

```text
demo@example.com / demo12345
```

## Verification

```bash
cd backend
python manage.py test
python manage.py run_due_publish

cd ../frontend
npm run build
```
