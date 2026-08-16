from apps.audit.models import MedicalRecordAccess


def record_medical_access(
    *,
    user,
    patient,
    object_type: str,
    action: str,
    object_id: str = "",
    purpose: str = "",
    request=None,
) -> MedicalRecordAccess:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    ip_address = (
        forwarded.split(",")[0].strip()
        if forwarded
        else request.META.get("REMOTE_ADDR")
        if request
        else None
    )
    return MedicalRecordAccess.objects.create(
        user=user,
        patient=patient,
        object_type=object_type,
        object_id=str(object_id),
        action=action,
        purpose=purpose,
        request_id=getattr(request, "request_id", "") if request else "",
        ip_address=ip_address or None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512] if request else "",
    )
