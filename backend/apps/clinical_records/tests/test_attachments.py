import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.clinical_records.models import MedicalFile, MedicalFileAttachment
from apps.hospital.models import ExternalHospital, ExternalHospitalSpecialty, Specialty
from apps.monitoring.tests.test_monitoring_workflow import monitoring_context
from apps.transfers.models import TransferTransmission


@pytest.mark.django_db
def test_attachment_upload_list_download_and_delete():
    doctor, _, guard, profile, patient = monitoring_context()
    medical_file = MedicalFile.objects.get(patient=patient)

    payload = b"%PDF-1.4 fake pdf content for the transfer package"
    client = APIClient()
    client.force_authenticate(doctor)
    response = client.post(
        reverse("clinical_records:medical-file-attachment-list"),
        {
            "patient": str(patient.id),
            "description": "Lab report from March",
            "file": SimpleUploadedFile(
                "lab_report.pdf", payload, content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["original_name"] == "lab_report.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["byte_size"] == len(payload)
    assert len(data["checksum"]) == 64
    assert data["uploaded_by_name"] == doctor.get_full_name()

    attachment = MedicalFileAttachment.objects.get(pk=data["id"])
    assert attachment.medical_file == medical_file
    assert attachment.patient == patient
    assert attachment.checksum == data["checksum"]

    # Download returns the original bytes with audit trail.
    download = client.get(
        reverse(
            "clinical_records:medical-file-attachment-download",
            kwargs={"pk": str(attachment.id)},
        )
    )
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == payload
    assert download["Content-Type"] == "application/pdf"

    # The Patient Guard can also download (audit-logged).
    guard_client = APIClient()
    guard_client.force_authenticate(guard)
    assert (
        guard_client.get(
            reverse(
                "clinical_records:medical-file-attachment-download",
                kwargs={"pk": str(attachment.id)},
            )
        ).status_code
        == 200
    )

    # Only clinical staff may upload.
    denied = guard_client.post(
        reverse("clinical_records:medical-file-attachment-list"),
        {
            "patient": str(patient.id),
            "file": SimpleUploadedFile("x.pdf", b"x", content_type="application/pdf"),
        },
        format="multipart",
    )
    assert denied.status_code == 403

    # Doctor can delete.
    assert (
        client.delete(
            reverse(
                "clinical_records:medical-file-attachment-detail",
                kwargs={"pk": str(attachment.id)},
            )
        ).status_code
        == 204
    )
    assert not MedicalFileAttachment.objects.filter(pk=attachment.id).exists()


@pytest.mark.django_db
def test_attachment_validation_rejects_oversized_and_disallowed_types():
    doctor, _, _, _, patient = monitoring_context()
    client = APIClient()
    client.force_authenticate(doctor)
    base = {
        "patient": str(patient.id),
        "file": SimpleUploadedFile(
            "script.exe", b"evil", content_type="application/x-msdownload"
        ),
    }
    assert (
        client.post(
            reverse("clinical_records:medical-file-attachment-list"), base, format="multipart"
        ).status_code
        == 400
    )
    base["file"] = SimpleUploadedFile(
        "big.pdf", b"x" * (11 * 1024 * 1024), content_type="application/pdf"
    )
    assert (
        client.post(
            reverse("clinical_records:medical-file-attachment-list"), base, format="multipart"
        ).status_code
        == 400
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_transfer_package_email_carries_uploaded_attachments(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    doctor, _, guard, profile, patient = monitoring_context()
    specialty = Specialty.objects.create(code="CARD", name="Cardiology")
    hospital = ExternalHospital.objects.create(
        name="Attachment Hospital",
        address="1 Road",
        city="Yaoundé",
        country="CM",
        phone="+237600000210",
        transfer_email="transfer@attachment.example.org",
    )
    ExternalHospitalSpecialty.objects.create(
        external_hospital=hospital,
        specialty=specialty,
        availability_status="AVAILABLE",
    )

    payload = b"%PDF-1.4 attachment payload"
    attachment = MedicalFileAttachment.objects.create(
        medical_file=MedicalFile.objects.get(patient=patient),
        patient=patient,
        uploaded_by=doctor,
        file=SimpleUploadedFile("scans.pdf", payload, content_type="application/pdf"),
        original_name="scans.pdf",
        mime_type="application/pdf",
        byte_size=len(payload),
        checksum="c" * 64,
    )

    client = APIClient()
    client.force_authenticate(doctor)
    created = client.post(
        reverse("transfers:transfer-request-list"),
        {
            "patient": str(patient.id),
            "guardian": str(profile.id),
            "reason": "Specialist care required",
            "clinical_summary": "Approved transfer summary",
            "urgency": "URGENT",
            "requirements": [
                {
                    "requirement_type": "SPECIALTY",
                    "specialty": str(specialty.id),
                    "weight": "5.00",
                    "is_mandatory": True,
                }
            ],
        },
        format="json",
    )
    transfer_id = created.json()["id"]
    assert client.post(
        reverse("transfers:transfer-request-recommend", kwargs={"pk": transfer_id})
    ).status_code == 200
    assert client.post(
        reverse("transfers:transfer-request-submit", kwargs={"pk": transfer_id}),
        {"hospital": str(hospital.id)},
        format="json",
    ).status_code == 200
    client.force_authenticate(guard)
    assert client.post(
        reverse("transfers:transfer-request-decide", kwargs={"pk": transfer_id}),
        {"decision": "APPROVE", "reason": "Approved"},
        format="json",
    ).status_code == 200

    client.force_authenticate(doctor)
    sent = client.post(
        reverse("transfers:transfer-request-send-package", kwargs={"pk": transfer_id})
    )
    assert sent.status_code == 200, sent.content
    assert TransferTransmission.objects.get().status == "SENT"

    email = mail.outbox[-1]
    names = [part.filename for part in email.attachments if part.filename]
    assert attachment.original_name in names
    packaged = next(
        part for part in email.attachments
        if part.filename == attachment.original_name
    )
    assert packaged.mimetype == "application/pdf"
    assert packaged.content == payload
    manifest = next(
        part for part in email.attachments
        if part.filename and part.filename.endswith(".json")
    )
    manifest_payload = manifest.content
    assert b"attachments" in manifest_payload
    assert b"scans.pdf" in manifest_payload
