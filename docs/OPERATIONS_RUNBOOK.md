# Operations Runbook

## Daily checks

- Admin dashboard: database healthy, reminder worker recent, no integration failures.
- Review failed login count and redacted audit anomalies.
- Review failed transfer transmissions and retry only after SMTP correction.
- Confirm disk capacity for SQLite, WAL, media, and backups.
- Confirm latest encrypted off-host backup.

## Common incidents

### Medication alerts stop

1. Check Admin scheduler heartbeat.
2. Inspect the worker service status/log.
3. Restart one worker using `process_medication_due --watch --interval 30`.
4. The worker is idempotent; dedupe keys prevent duplicate alerts.
5. Verify a due dose receives one notification.

### SQLite busy/locked errors

1. Confirm only the supported primary ASGI process and known worker are running.
2. Confirm the database is on a local filesystem.
3. Identify long transactions or unauthorized scripts.
4. Do not delete WAL/SHM files while processes run.
5. Back up before intervention.

### SMTP transfer fails

1. Preserve the failed `TransferTransmission` record.
2. Validate SMTP host, TLS, sender, recipient, and provider health.
3. Confirm the transfer remains Guard-approved.
4. Retry from the Doctor workflow; do not mark sent manually.
5. Verify provider success, checksum, recipient, and audit event.

### Twilio unavailable

1. The UI should show integration unavailable, not a fake call.
2. Confirm every `TWILIO_*` variable and public webhook URL.
3. Verify the TwiML application Voice URL.
4. Check TLS and signed webhook validation.
5. Review persisted webhook processing errors.

### Suspected unauthorized access

1. Disable the account without deleting it.
2. Preserve database, logs, audit events, and access records.
3. Rotate affected sessions/secrets and provider credentials.
4. Follow hospital incident policy and legal notification rules.
5. Restore service only after containment and documented approval.

## Release procedure

1. Back up database and media.
2. Run backend and frontend verification commands from README.
3. Review migrations and environment changes.
4. Deploy built assets and Python code.
5. Stop worker, stop ASGI, migrate once, start ASGI, start worker.
6. Perform role-scoped smoke tests.
7. Monitor errors, locks, SMTP, Twilio, and heartbeat.

## Rollback

Code-only rollback is allowed only when schema compatibility is confirmed. For incompatible migrations, use the approved pre-release backup and full restore procedure. Never improvise a production schema downgrade without testing.
