# Production Readiness Checklist

## Product and clinical policy

- [ ] Roles and permission matrix approved by hospital leadership.
- [ ] Vital metrics/rules supplied and approved by clinical governance.
- [ ] Medication missed-dose policy approved.
- [ ] Transfer consent wording and package contents approved.
- [ ] Death certificate fields/numbering reviewed for jurisdiction.
- [ ] Financial catalogue, ISO 4217 billing currency, reversal, and receipt policy approved.
- [ ] Data retention and account offboarding policy approved.

## Security

- [ ] Threat model reviewed.
- [ ] Production secrets injected outside Git.
- [ ] TLS, HSTS, hosts, origins, cookies, CSP, and WebSocket proxy verified.
- [ ] Cross-patient UUID regression suite passes.
- [ ] Attachment malware/quarantine policy implemented where required.
- [ ] Admin has no default clinical access.
- [ ] Audit/access logs protected from ordinary modification.
- [ ] SMTP and Twilio credentials scoped and rotated.

## Data and resilience

- [ ] SQLite on encrypted local persistent storage.
- [ ] One-primary ASGI topology enforced.
- [ ] WAL/busy-timeout behavior load tested.
- [ ] Encrypted off-host backup schedule configured.
- [ ] Restore drill passed and documented.
- [ ] Disk, backup, heartbeat, and integration monitoring configured.

## Quality

- [ ] Backend tests, Ruff, Django checks, and migration drift pass.
- [ ] Frontend tests, TypeScript, ESLint, build, and npm audit pass.
- [ ] End-to-end role handoffs pass in a staging copy.
- [ ] Keyboard, screen reader, focus, reduced motion, tablet, mobile, and print reviewed.
- [ ] Empty, loading, forbidden, not-found, conflict, and provider-failure states reviewed.

## Operations

- [ ] Deployment guide followed in staging.
- [ ] Worker and ASGI service definitions tested.
- [ ] SMTP transfer and invitation delivery tested.
- [ ] Twilio signed webhooks tested or calling intentionally disabled.
- [ ] Incident, downtime, backup, rollback, and on-call owners assigned.
- [ ] Role training complete.
- [ ] Final release sign-off recorded.
