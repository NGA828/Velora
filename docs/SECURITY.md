# Velora Security Model

## Trust boundaries

- React is an untrusted client and never authorizes data by itself.
- Django authenticates, scopes, validates, transitions, and audits every protected workflow.
- SQLite and protected media are reachable only by application/operations accounts.
- SMTP and Twilio are external providers behind isolated adapters.

## Authentication

- Public registration is disabled.
- Accounts use role-restricted, hashed, expiring invitation tokens.
- Browser authentication uses an `HttpOnly` Django session cookie.
- State-changing requests require CSRF protection.
- Passwords use Argon2 first, with Django's supported fallback hashers.
- Temporary-password users are blocked from all other APIs until changing the password.
- Login, invitation, communication, call, payment, transfer, and clinical writes are rate scoped.

## Authorization

Role checks are only the first gate. Patient data also requires an active relationship:

- Doctor/Nurse: active `PatientCareAssignment`
- Patient Guard: active `GuardianAccess` plus feature-specific permission
- Accounting: billing identity and financial records only
- Head of Service: operational aggregates/configuration, not blanket medical records
- Admin: identity, health, and redacted audit metadata, not medical content

Detail endpoints begin from a user-scoped queryset. An unauthorized UUID resolves as not found rather than returning a protected object.

## Clinical integrity

- No hard-coded medical thresholds are shipped.
- Incomplete vital-rule coverage produces Unassessed, never Stable.
- Rule versions and evaluation snapshots preserve historical explanations.
- Signed notes, dose events, transfer decisions, payment reversals, and issued/void certificates are append-only or transition controlled.
- Medical file views/downloads/transmissions are separately logged.

## Transport and browser controls

Production enforces secure cookies, HTTPS redirect, HSTS, trusted hosts/origins, frame denial, content-type sniffing prevention, restrictive CSP, no-store API caching, and a microphone-only permissions policy for same-origin Twilio use.

The reverse proxy must support TLS and authenticated WebSocket upgrades.

## Uploads

Message attachments are limited to 10 MB and an explicit extension/MIME allowlist. PDF, PNG, JPEG, and UTF-8 text signatures are checked. Downloads require active conversation membership, force attachment disposition, add `nosniff`, and use a restrictive response CSP.

Content-signature checks are not a malware scanner. A production hospital should add provider/host malware scanning and quarantine if required by policy.

## Secrets and logs

- Secrets are environment supplied.
- Passwords, sessions, invitation tokens, provider secrets, and medical bodies are not logged.
- Audit snapshot recording redacts known secret keys.
- Admin audit APIs deliberately omit before/after snapshots.
- Twilio webhook signatures are verified before state changes.

## Storage and backup

- Keep SQLite on a local persistent encrypted volume, never NFS/SMB.
- Restrict database and media permissions to the service account.
- Use `backup_velora` for SQLite's online backup API and checksummed media archives.
- Store backups encrypted and off host, with access logging and retention policy.
- Test restore in an isolated environment.

## Known deployment constraints

SQLite is not a horizontally scalable writer. The local Channels layer does not broadcast across processes. The supported initial deployment is one primary ASGI process plus controlled workers. Do not increase web worker count without an approved architecture change.

## Compliance statement

This design supports privacy, least privilege, auditability, and integrity controls. It does not itself certify compliance with a specific jurisdiction. Hospital policy, legal review, infrastructure, retention, incident response, staff training, and operational evidence remain required.
