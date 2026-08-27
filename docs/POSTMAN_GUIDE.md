# Testing the Velora API with Postman

This guide explains how to exercise the Velora backend (Django REST Framework) from
[Postman](https://www.postman.com/). A ready-to-import collection is included at the
repository root: **`Velora.postman_collection.json`**.

## 1. Why this API is a bit special: sessions + CSRF

Velora does **not** use token auth. It uses:

- **Server-side session auth** — the login response sets a session cookie named `velora_session`. Postman's built-in cookie jar stores and replays it automatically.
- **CSRF protection** — every unsafe request (`POST` / `PUT` / `PATCH` / `DELETE`) must send the current CSRF token in the `X-CSRFToken` header. The token comes from the `velora_csrftoken` cookie (or the JSON body of the CSRF endpoint).
- **Token rotation** — Django **rotates the CSRF token when you log in**. The token you fetched before login becomes stale; use the new one from the post-login cookie jar.

## 2. Start the backend

```bash
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_demo     # demo users + sample data
../.venv/bin/python -m uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

Base URL for all requests: `http://localhost:8000`. Health check: `GET http://localhost:8000/health/`.
All API routes live under `/api/v1/`.

Demo accounts (all with password `password123`): `admin@`, `head@`, `doctor@`, `nurse@`,
`guard@`, `accounts@velora.com`.

## 3. Fastest path: import the included collection

1. In Postman: **Import → `Velora.postman_collection.json`** (from the repo root).
2. Open the collection, folder **`0 · Setup & Auth`**:
   1. Send **`1 · Get CSRF token`** — `GET /api/v1/auth/csrf/`. The test script saves the token.
   2. Send **`2 · Login`** — `POST /api/v1/auth/login/` with `{{email}}` / `{{password}}`. The script saves the *rotated* CSRF token automatically.
3. Now run anything else in the collection.

The collection automates all the tricky parts:

| Automation | Where |
| --- | --- |
| Attaches `X-CSRFToken` to every `POST/PUT/PATCH/DELETE` | collection pre-request script |
| Saves the CSRF token from the CSRF endpoint | test script on `1 · Get CSRF token` |
| Re-reads the **rotated** token after login | test script on `2 · Login` |
| Keeps the session cookie | Postman cookie jar (automatic) |
| Captures IDs (`patient_id`, `department_id`, `nurse_id`, …) into variables | test scripts on list requests |

Run order tip: before **Create patient**, run **Departments** and **Clinical directory**
(they fill `{{department_id}}` / `{{nurse_id}}`), and log in as `doctor@velora.com` —
patient creation is role-scoped and **Admin gets `permission_denied`**.

## 4. Doing it manually (no collection)

If you prefer to set it up by hand:

1. **Get a CSRF token**
   `GET http://localhost:8000/api/v1/auth/csrf/`
   → copy `csrf_token` from the JSON body (also set as the `velora_csrftoken` cookie).
2. **Log in** (Postman tab: Body → raw → JSON)
   `POST http://localhost:8000/api/v1/auth/login/`
   Headers: `Content-Type: application/json`, `X-CSRFToken: <token from step 1>`
   Body: `{"email": "admin@velora.com", "password": "password123"}`
   → response sets the `velora_session` cookie (stored in Postman's cookie jar automatically).
3. **Refresh the CSRF token** — after login the old one is invalid. Open the **Cookies** link
   under the Send button in Postman, find `velora_csrftoken` for `localhost`, and use that
   value in the `X-CSRFToken` header for subsequent writes.
4. **Call any endpoint** — `GET` requests need no CSRF header; writes need the current
   `X-CSRFToken`. The session cookie is sent automatically by Postman.

## 5. Role matrix quick reference (verified)

| Account | Role | Example of what works |
| --- | --- | --- |
| `admin@velora.com` | Admin | staff lists, invitations, reports, dashboards — **not** patient creation |
| `head@velora.com` | Head Doctor | clinical writes + department oversight |
| `doctor@velora.com` | Doctor | create patients, prescriptions, diagnoses, assign nurses |
| `nurse@velora.com` | Nurse | vitals, medication doses, invite Patient Guards |
| `guard@velora.com` | Patient Guard | limited, guard-scoped patient views |
| `accounts@velora.com` | Billing | billing dashboards, invoices, financial reports |

## 6. Common errors and fixes

| Response | Cause | Fix |
| --- | --- | --- |
| `403` "CSRF Failed: CSRF token … missing" | No `X-CSRFToken` header on a write | Add the header (collection does this for you) |
| `403` "CSRF token … incorrect" | Stale token — usually the pre-login token after logging in | Re-send **Login** (script refreshes it) or re-read the `velora_csrftoken` cookie |
| `401/403` "Authentication credentials were not provided" | No session cookie | Run **Get CSRF token** → **Login** again |
| `403` `permission_denied` | Your role isn't allowed | Log in with a role that has the capability (see §5) |
| `400` `validation_error` with `fields` | Missing/invalid body fields | The `fields` object lists every offending field |
| Empty replies / connection refused | Backend not running | Start uvicorn (§2), check port 8000 |

## 7. Endpoint map (all under `/api/v1/`)

- **Auth:** `auth/csrf/`, `auth/login/`, `auth/logout/`, `auth/session/`, `auth/me/`, `auth/password/change/`
- **Staff:** `staff/`, `staff/{id}/`, `staff/clinical-directory/`, `staff/invitations/`
- **Hospital:** `hospital/` (API index), `hospital/profile/`, `hospital/dashboard/`, `hospital/departments/`, `rooms/`, `beds/`, `services/`, `external-hospitals/` …
- **Patients:** `patients/`, `patients/{id}/`, `patients/{id}/guardians/`, `patients/{id}/assign-nurse/`, `patients/dashboard/`
- **Clinical records:** `medical-files/`, `medical-file-attachments/`, `allergies/`, `medical-history/`, `diagnoses/`, `treatment-plans/`, `clinical-notes/`
- **Prescriptions:** `medications/`, `prescriptions/`, `medication-doses/`
- **Vitals & monitoring:** `vital-metrics/`, `vital-rule-sets/`, `vital-rules/`, `vital-observations/`, `vital-observations/icu-recommendations/`, `monitoring-threads/`
- **Transfers & certificates:** `transfer-requests/`, `death-certificates/`
- **Messaging:** `conversations/`, `conversations/{id}/messages/`, `conversations/{id}/seen/`
- **Billing & reports:** `billing/dashboard/`, `billing/patients/`, `reports/financial/`, `reports/financial/export/`, `reports/operational/`, `system/dashboard/`
- **Notifications:** `notifications/`, `notifications/{id}/read/`, `notifications/read-all/`
- **AI assistant:** `clinical-assistant/chat/` (`{"patient_id": "<uuid>", "message": "…"}`)
- **Webhooks:** `integrations/twilio/voice/`, `integrations/twilio/status/`
- **Health:** `GET /health/` (no `/api/v1` prefix, no auth)

Tip: many routers expose a browsable index — `GET /api/v1/hospital/` lists every hospital
sub-endpoint. Real-time features (alerts, calls) use WebSockets, which Postman tests via
**File → New → WebSocket** against `ws://localhost:8000/ws/…` with the same session cookie.
