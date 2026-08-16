import hashlib
import io
import json
import tarfile

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.common.backup import _safe_extract, load_and_verify_manifest


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_demo_seed_uses_dot_com_accounts_and_requested_password():
    call_command("seed_demo", verbosity=0)

    from apps.identity.models import User

    expected = {
        "admin@velora.com",
        "head@velora.com",
        "doctor@velora.com",
        "nurse@velora.com",
        "guard@velora.com",
        "accounts@velora.com",
    }
    users = User.objects.filter(email__in=expected)
    assert set(users.values_list("email", flat=True)) == expected
    assert all(user.check_password("password123") for user in users)
    assert not User.objects.filter(email__endswith=".local").exists()


@pytest.mark.django_db
def test_api_responses_disable_caching_and_set_browser_security_headers():
    response = APIClient().get(reverse("identity:csrf"))

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store, private"
    assert "default-src 'self'" in response["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert "microphone=(self)" in response["Permissions-Policy"]
    assert response["Cross-Origin-Resource-Policy"] == "same-origin"


def test_backup_manifest_detects_checksum_tampering(tmp_path):
    database = tmp_path / "velora.sqlite3"
    database.write_bytes(b"valid backup bytes")
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "format": "velora-backup-v1",
                "files": {"database": {"name": database.name, "sha256": digest}},
            }
        ),
        encoding="utf-8",
    )
    assert load_and_verify_manifest(tmp_path)["format"] == "velora-backup-v1"

    database.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_and_verify_manifest(tmp_path)


def test_media_restore_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"escape"
        info = tarfile.TarInfo("../outside.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    destination = tmp_path / "destination"
    destination.mkdir()

    with tarfile.open(archive_path, "r:gz") as archive:
        with pytest.raises(ValueError, match="Unsafe path"):
            _safe_extract(archive, destination)
    assert not (tmp_path / "outside.txt").exists()
