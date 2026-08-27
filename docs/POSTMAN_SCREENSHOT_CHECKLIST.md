# Postman Screenshot Checklist — Velora API

Use this to capture your own evidence screenshots in the Postman desktop app.
Import `Velora.postman_collection.json` first, keep the backend running
(`uvicorn config.asgi:application --port 8000`), then capture each screen below in order.

**What every screenshot should show:** request name tab, method + URL bar, the active
tab (Body for writes), the status pill (`200 OK` / `201 Created` …), time/size, and the
response body. Keep the response body visible — crop nothing.

Legend: 🟢 expected success · 🔴 deliberate failure (proves security works)

## A. Authentication & security (screenshots 1–5)

| # | Collection request | Login as | Expected | What it proves |
|---|---|---|---|---|
| 1 | `GET /health/` | — | 🟢 200 | Server up |
| 2 | `0 · Setup & Auth → 1 · Get CSRF token` | — | 🟢 200 + `csrf_token` | CSRF flow works |
| 3 | `2 · Login` **after deleting the `X-CSRFToken` header** | — | 🔴 403 CSRF Failed | CSRF protection enforced |
| 4 | `2 · Login` (restore header, default vars) | `admin@velora.com` | 🟢 200 + user object | Session issued |
| 5 | `3 · Current session` | admin | 🟢 200 | Cookie-jar session works |

## B. Admin / hospital (screenshots 6–8)

| # | Request | Login as | Expected |
|---|---|---|---|
| 6 | `1 · Identity & Staff → Staff list` | admin | 🟢 200, paginated staff |
| 7 | `2 · Hospital → Hospital dashboard` | **admin** | 🔴 403 permission_denied — dashboards are clinical-role-scoped (re-run as `head@velora.com` for 🟢) |
| 8 | `2 · Hospital → Departments` | any staff | 🟢 200 (fills `{{department_id}}`) |

## C. Clinical workflow as doctor (screenshots 9–14)

Run `1 · Identity → Clinical directory` first (fills `{{nurse_id}}`), and log in as
`doctor@velora.com` for all of section C.

| # | Request | Expected |
|---|---|---|
| 9 | Login as doctor | 🟢 200, role DOCTOR |
| 10 | `3 · Patients → Patient list` | 🟢 200 (fills `{{patient_id}}`) |
| 11 | `Create patient` with an **empty body** `{}` | 🔴 400 validation_error listing every required field |
| 12 | `Create patient` with the full sample body | 🟢 201 Created + `medical_record_number` |
| 13 | `Patient detail` | 🟢 200, shows the new patient |
| 14 | `Update patient` (PATCH) | 🟢 200 with updated `address` |

## D. Other domains (screenshots 15–20)

| # | Request | Login as | Expected |
|---|---|---|---|
| 15 | `5 · Prescriptions → Prescriptions` | doctor | 🟢 200 |
| 16 | `6 · Vitals → Vital observations` | doctor | 🟢 200 |
| 17 | `6 · Vitals → Monitoring threads` | doctor | 🟢 200 |
| 18 | Login as `accounts@velora.com` | — | 🟢 200, role BILLING |
| 19 | `9 · Billing → Billing dashboard` | accounts | 🟢 200 |
| 20 | `9 · Billing → Financial report` | accounts | 🟢 200 |

## E. Teardown (screenshot 21)

| # | Request | Expected |
|---|---|---|
| 21 | `Logout` | 🟢 204 No Content |

## Tips for clean screenshots

- Use **File → New tab** per request so the tab title shows the request name.
- Press **Alt/Option + click** the response pane divider to expand the response fully.
- For POST/PATCH shots, keep the **Body** tab active so your grader sees the JSON you sent.
- Include the collection sidebar (visible when no other panel is expanded) in at least
  screenshots 4 and 12 — it shows the full test surface.
- Ready-made fallback: `postman-screens/Velora_API_Test_Evidence.pdf` contains all 21
  captures above, rendered from real live responses — usable as documentation, but capture
  your own in the Postman app if your submission requires the actual tool.
