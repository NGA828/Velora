from apps.identity.models import UserRole

ROLE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    UserRole.ADMIN: (
        "users.manage",
        "system.manage",
        "audit.security.read",
    ),
    UserRole.HEAD_OF_SERVICE: (
        "staff.manage",
        "hospital.manage",
        "vital_rules.manage",
        "reports.operational.read",
    ),
    UserRole.DOCTOR: (
        "patients.register",
        "patients.assigned.read",
        "medical_records.clinical.manage",
        "prescriptions.manage",
        "monitoring.manage",
        "transfers.manage",
        "death_certificates.manage",
    ),
    UserRole.NURSE: (
        "patients.assigned.read",
        "patient_guards.manage",
        "vitals.record",
        "medication.administer",
    ),
    UserRole.PATIENT_GUARD: (
        "patients.linked.read",
        "monitoring.respond",
        "prescriptions.linked.read",
        "transfers.decide",
        "death_certificates.issued.read",
    ),
    UserRole.ACCOUNTING: (
        "billing.manage",
        "reports.financial.read",
    ),
}


def capabilities_for_role(role: str) -> tuple[str, ...]:
    return ROLE_CAPABILITIES.get(role, ())
