import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_path() -> Path:
    config = settings.DATABASES["default"]
    if config["ENGINE"] != "django.db.backends.sqlite3" or str(config["NAME"]) == ":memory:":
        raise ImproperlyConfigured("Backup and restore require a file-backed SQLite database.")
    return Path(config["NAME"]).resolve()


def create_backup(output_root: Path) -> Path:
    source_database = database_path()
    if not source_database.exists():
        raise FileNotFoundError(f"SQLite database not found: {source_database}")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = output_root.resolve() / f"velora-backup-{stamp}"
    suffix = 1
    while backup_dir.exists():
        backup_dir = output_root.resolve() / f"velora-backup-{stamp}-{suffix}"
        suffix += 1
    backup_dir.mkdir(parents=True)

    database_backup = backup_dir / "velora.sqlite3"
    with sqlite3.connect(source_database) as source, sqlite3.connect(database_backup) as target:
        source.backup(target)
    files = {
        "database": {
            "name": database_backup.name,
            "sha256": sha256_file(database_backup),
            "bytes": database_backup.stat().st_size,
        }
    }

    media_root = Path(settings.MEDIA_ROOT).resolve()
    if media_root.exists() and any(media_root.iterdir()):
        media_backup = backup_dir / "media.tar.gz"
        with tarfile.open(media_backup, "w:gz") as archive:
            archive.add(media_root, arcname="media", recursive=True)
        files["media"] = {
            "name": media_backup.name,
            "sha256": sha256_file(media_backup),
            "bytes": media_backup.stat().st_size,
        }

    manifest = {
        "format": "velora-backup-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "database_engine": "sqlite3",
        "files": files,
        "migrations": [
            f"{app}.{name}"
            for app, name in MigrationRecorder.Migration.objects.values_list("app", "name")
        ],
    }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return backup_dir


def load_and_verify_manifest(backup_dir: Path) -> dict:
    backup_dir = backup_dir.resolve()
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("Backup manifest.json was not found.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "velora-backup-v1":
        raise ValueError("Unsupported Velora backup format.")
    for metadata in manifest.get("files", {}).values():
        path = backup_dir / metadata["name"]
        if not path.is_file() or sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"Backup checksum validation failed for {metadata['name']}.")
    return manifest


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (root / member.name).resolve()
        if root not in target.parents and target != root:
            raise ValueError("Unsafe path detected in media archive.")
        if member.issym() or member.islnk() or member.isdev():
            raise ValueError("Links and device entries are not allowed in media archives.")
    archive.extractall(root)


def restore_backup(backup_dir: Path) -> dict:
    backup_dir = backup_dir.resolve()
    manifest = load_and_verify_manifest(backup_dir)
    target_database = database_path()
    database_backup = backup_dir / manifest["files"]["database"]["name"]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    connections.close_all()
    if target_database.exists():
        safety_copy = target_database.with_name(f"{target_database.name}.pre-restore-{stamp}")
        shutil.copy2(target_database, safety_copy)
    temporary_database = target_database.with_name(f".{target_database.name}.restore-{os.getpid()}")
    shutil.copy2(database_backup, temporary_database)
    os.replace(temporary_database, target_database)

    media_metadata = manifest["files"].get("media")
    if media_metadata:
        media_root = Path(settings.MEDIA_ROOT).resolve()
        extraction_root = media_root.parent / f".velora-media-restore-{os.getpid()}"
        if extraction_root.exists():
            shutil.rmtree(extraction_root)
        extraction_root.mkdir(parents=True)
        with tarfile.open(backup_dir / media_metadata["name"], "r:gz") as archive:
            _safe_extract(archive, extraction_root)
        extracted_media = extraction_root / "media"
        if media_root.exists():
            media_safety = media_root.with_name(f"{media_root.name}.pre-restore-{stamp}")
            os.replace(media_root, media_safety)
        os.replace(extracted_media, media_root)
        shutil.rmtree(extraction_root, ignore_errors=True)
    return manifest
