# Velora

Velora is a secure, domain-organized Hospital Management System for one hospital. It connects hospital configuration, staff, patient care, Patient Guards, vital alerts, prescriptions, medication administration, transfers, communication, billing, and audit history through role-scoped workflows.

> **Current delivery:** Phase 10 final acceptance — complete connected workflows, role-matrix regression coverage, configurable invoice currency snapshots, reproducible demo data, resilience tooling, CI, and production-readiness documentation.

Documentation:

- [System design](docs/SYSTEM_DESIGN.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Security model](docs/SECURITY.md)
- [Backup and restore](docs/BACKUP_RESTORE.md)
- [Operations runbook](docs/OPERATIONS_RUNBOOK.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Acceptance test plan](docs/ACCEPTANCE_TEST_PLAN.md)

## Technology

- React, Vite, TypeScript, React Router, Axios, TanStack Query
- Django 5.2, Django REST Framework, Django Channels
- SQLite with Django migrations
- Server-side session authentication, CSRF protection, Argon2 password hashing
- Pytest, Ruff, Vitest, ESLint, and TypeScript checks

## Local setup

### 1. Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements/local.txt
cd backend
../.venv/bin/python manage.py migrate
```

For the local demonstration environment only, create all six role accounts and connected sample data with:

```bash
../.venv/bin/python manage.py seed_demo
```

The demo credentials are `admin@velora.com`, `head@velora.com`, `doctor@velora.com`, `nurse@velora.com`, `guard@velora.com`, and `accounts@velora.com`, all using `password123`. This intentionally simple password is restricted to the `DEBUG=True` demo command and must never be used for production accounts.

Create the first production/staging Admin without putting its password in shell history:

```bash
export VELORA_BOOTSTRAP_PASSWORD='choose-a-long-private-password'
../.venv/bin/python manage.py bootstrap_admin \
  --email admin@example.org \
  --first-name System \
  --last-name Administrator \
  --employee-number ADM-001 \
  --no-input
unset VELORA_BOOTSTRAP_PASSWORD
```

Run Django/ASGI:

```bash
../.venv/bin/python -m uvicorn config.asgi:application \
  --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Browser requests use relative `/api` paths; Vite proxies them to Django.

Run the idempotent medication-due worker in another terminal when testing active prescriptions:

```bash
cd backend
../.venv/bin/python manage.py process_medication_due --watch --interval 30
```

Voice calling remains disabled unless every Twilio setting in `.env.example` is configured. The TwiML application voice URL must point to `/api/v1/integrations/twilio/voice/`, and status callbacks are signature-validated at `/api/v1/integrations/twilio/status/`.

## Verification

```bash
# Backend
cd backend
../.venv/bin/ruff check .
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/pytest

# Frontend
cd frontend
npm run typecheck
npm run lint
npm run test:run
npm run build
npm audit
```

## Security defaults

- Public registration is disabled.
- Accounts are created through role-restricted, expiring invitations.
- Browser credentials use an `HttpOnly` server session; no auth token is stored in local storage.
- State-changing requests require CSRF protection.
- Temporary-password accounts cannot use other APIs before changing their password.
- Role capability metadata helps the UI, but backend permissions remain authoritative.
- Admin and Head of Service roles do not receive automatic patient-record access.
- Secrets belong in environment variables; see [`.env.example`](.env.example).
- Runtime SQLite, media, static build, environment, and dependency files are ignored by Git.

## Repository structure

```text
backend/    Django API, domain applications, integrations, migrations and tests
frontend/   React application, role modules, shared UI, API client and tests
docs/       Architecture and product design documentation
```

The planned product workflows are implemented. Remaining production release work is hospital-specific policy approval, staging acceptance, infrastructure configuration, operational training, and completion of the production-readiness checklist.
