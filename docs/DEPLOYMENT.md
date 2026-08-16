# Velora Deployment Guide

## Supported topology

Velora is a single-hospital application with SQLite as its only system-of-record database. The supported initial topology is:

```text
TLS reverse proxy
├── /                 → built React application
├── /api and /health  → one primary Django ASGI process
└── /ws               → the same Django ASGI process

Medication reminder worker → same release and SQLite file
Protected media            → local encrypted persistent volume
```

SQLite and the in-memory Channels layer make this a **single-primary application process** deployment. Do not run multiple independent ASGI workers: WebSocket groups would not cross process boundaries, and concurrent SQLite writes would become less predictable. A future multi-process topology requires an approved channel broker and database migration; neither is silently introduced here.

## Host prerequisites

- Python 3.11+
- Node.js 22+
- A persistent, non-network-mounted filesystem
- TLS termination with WebSocket proxy support
- Encrypted host volume and encrypted backups
- SMTP account for invitation and transfer delivery
- Optional Twilio Voice application

## Build

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements/production.txt

cd frontend
npm ci
npm run build
cd ..

cd backend
../.venv/bin/python manage.py migrate --noinput
../.venv/bin/python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.production \
  ../.venv/bin/python manage.py check --deploy
```

Publish `frontend/dist` as the web root. Do not publish `backend/media`; downloads are authorized through Django.

## Required environment

At minimum:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<long random value>
DJANGO_ALLOWED_HOSTS=hospital.example.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://hospital.example.org
SQLITE_PATH=/srv/velora/data/velora.sqlite3
MEDIA_ROOT=/srv/velora/media
FRONTEND_URL=https://hospital.example.org
HOSPITAL_TIME_ZONE=Africa/Lagos
```

Configure SMTP variables from `.env.example`. Secrets must be injected by the service manager or secret store, not committed to the repository.

## ASGI process

```bash
cd /srv/velora/backend
../.venv/bin/python -m uvicorn config.asgi:application \
  --host 0.0.0.0 --port 8000 --proxy-headers
```

Use one ASGI process for the supported SQLite/in-memory-channel topology. Configure process restart and a filesystem-backed working directory.

## Medication worker

```bash
cd /srv/velora/backend
../.venv/bin/python manage.py process_medication_due --watch --interval 30
```

The worker writes a heartbeat read by the Admin dashboard. A heartbeat older than 90 seconds is marked stale.

## Reverse proxy requirements

- Redirect HTTP to HTTPS.
- Proxy `/api/` and `/health/` to Django.
- Proxy `/ws/` with HTTP/1.1 upgrade headers.
- Serve the React `index.html` fallback for client routes.
- Preserve `Host` and `X-Forwarded-Proto`.
- Set upload limits at least as large as Django's configured limit, but not larger than hospital policy.
- Do not cache authenticated API responses.

## Twilio Voice

Set all Twilio variables, including `TWILIO_WEBHOOK_BASE_URL`. Configure the TwiML application's Voice URL as:

```text
https://hospital.example.org/api/v1/integrations/twilio/voice/
```

Velora supplies signed status callback URLs under `/api/v1/integrations/twilio/status/`. Calling stays disabled until the complete configuration is present.

## Post-deployment smoke test

1. `GET /health/` returns `{"status":"ok"}`.
2. Admin dashboard reports database healthy and worker online.
3. Login and logout preserve CSRF protections.
4. Two authorized preview/training users exchange a message and observe Sent → Delivered → Seen.
5. Create a nonclinical test invoice and reverse its test payment.
6. Create and restore a backup in a separate verification environment.
7. Confirm protected media cannot be fetched directly from the static server.
