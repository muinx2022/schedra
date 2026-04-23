FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

RUN groupadd --system app && \
    useradd --system --gid app --create-home --home-dir /home/app app

COPY --chown=app:app backend /app/backend

RUN mkdir -p /app/backend/.celery /app/backend/media /app/backend/staticfiles && \
    chown -R app:app /app/backend /home/app

USER app

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]
