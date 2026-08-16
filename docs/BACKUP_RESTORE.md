# Backup and Restore Runbook

## Create an online backup

The command uses SQLite's online backup API, then archives protected media and writes SHA-256 checksums:

```bash
cd backend
../.venv/bin/python manage.py backup_velora \
  --output-dir /srv/velora/backups
```

A timestamped directory contains:

```text
manifest.json
velora.sqlite3
media.tar.gz       # only when protected media exists
```

Copy the completed directory to encrypted off-host storage. Never expose it through the web server.

## Verify before relying on a backup

- Inspect `manifest.json` and confirm `velora-backup-v1`.
- Confirm the database and media checksums in the destination.
- Open the copied SQLite database with `PRAGMA integrity_check;` in an isolated environment.
- Periodically restore into a non-production host and execute workflow smoke tests.

## Restore

**This replaces the live database and protected media.**

1. Announce downtime and stop the ASGI process.
2. Stop the medication worker and all management jobs.
3. Snapshot the host volume if available.
4. Run:

```bash
cd backend
../.venv/bin/python manage.py restore_velora \
  /srv/velora/backups/velora-backup-YYYYMMDDTHHMMSSZ \
  --confirm RESTORE
```

The command verifies every manifest checksum before replacement and creates `.pre-restore-<timestamp>` safety copies of the existing database/media.

5. Run:

```bash
../.venv/bin/python manage.py migrate --noinput
../.venv/bin/python manage.py check
../.venv/bin/python manage.py showmigrations --plan
```

6. Start one ASGI process, then the medication worker.
7. Verify `/health/`, Admin system health, role login, one scoped patient lookup, protected attachment download, and notification processing.
8. Record who restored, source backup, reason, checksums, timing, and validation result.

## Security behavior

Restore rejects unsupported manifests, checksum mismatches, path traversal, archive links, and device entries. It refuses in-memory or non-SQLite databases.

## Recovery objectives

The hospital must approve RPO/RTO targets. Schedule frequency and off-host copy cadence from those targets; the application does not silently choose a clinical retention policy.
