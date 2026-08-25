# Velora Hospital Management System — System Design Document

**Status:** Proposed for review
**Version:** 1.0
**Date:** 2026-08-16
**Implementation status:** Architecture only; no application code has been created.

---

## 0. Executive decisions

Velora will be a **single-hospital clinical operations system**, not a multi-tenant SaaS product. It will be delivered as vertical, end-to-end workflows rather than as a collection of unrelated pages.

The proposed baseline is:

- **Frontend:** React + Vite + TypeScript, React Router, Axios, TanStack Query, React Hook Form, and schema-based validation.
- **Backend:** Django + Django REST Framework, served through ASGI so REST and real-time events can share one application.
- **Database:** SQLite as the only system-of-record database, managed exclusively through Django migrations.
- **Authentication:** Secure Django server-side sessions in `HttpOnly` cookies with CSRF protection. Authentication material is never stored in browser local storage.
- **Authorization:** Role checks plus object-level patient access policies. A role alone never grants access to every patient.
- **Real-time behavior:** Durable REST/database writes first, followed by WebSocket notifications for messaging and alerts. REST synchronization remains the recovery path.
- **Scheduled work:** Idempotent Django management workers invoked by the local process manager or production scheduler; no separate queue or database is required.
- **Identifiers:** UUID public identifiers, hospital MRNs for patients, and human-readable certificate/invoice/employee numbers.
- **Clinical safety:** No medical thresholds are embedded in source code. Versioned, auditable rule sets determine vital-sign classifications.
- **Integration secrets:** SMTP, Twilio, Django, and deployment secrets live in environment variables, never in SQLite or Git.

The repository currently contains only a minimal README, so this is a greenfield architecture with no legacy code constraints.

---

# A. Project synthesis

## A.1 Product understanding

The Head of Service first establishes the operational context: hospital profile, departments, specialties, condition-to-specialty mappings, services, rooms, beds, resources, external transfer hospitals, and staff accounts. Doctor and Nurse access is therefore based on configured personnel rather than anonymous registration.

A Doctor registers a patient and assigns an active Nurse. Registration creates more than a demographic row: it creates the patient's medical file, care episode, care-team assignments, audit trail, and an assignment notification. The assigned Nurse can then invite or create a Patient Guard and grant that guard access to the correct patient. A guard account may be linked to more than one patient, but every link is explicit and revocable.

Care then proceeds through connected clinical workflows:

1. The Nurse records a structured set of vital observations.
2. A versioned rules engine evaluates those values against hospital-configured rules.
3. The system records both the classification and the explanation.
4. If a configured critical rule matches, the actively assigned Doctor receives a durable alert.
5. The Doctor reviews the patient's authorized clinical history and can diagnose, document treatment, prescribe, monitor, or initiate transfer.

Prescriptions become visible to the authorized guard and generate concrete scheduled medication doses for the assigned Nurse. Each dose moves through controlled states and records the scheduled time, actual time, Nurse, outcome, and notes.

Monitoring is modeled as a persistent clinical conversation. A Doctor opens a monitoring thread and asks typed questions. The linked Patient Guard responds; responses are append-only or supersede an earlier response so history is not erased. The Doctor is notified and may continue with new questions.

For transfer, the Doctor declares clinical requirements instead of asking an opaque algorithm for a result. A rule-based service compares required specialties and services with active external-hospital capabilities, produces a ranked explanation, and stores the recommendation snapshot. The Doctor selects a destination and submits the request to a designated Patient Guard. Only after approval can the Doctor transmit an authorized medical-file package through SMTP. Every decision and transmission attempt is auditable.

If a patient dies, only an authorized Doctor may draft and issue a death certificate. The linked guard may view and print an issued certificate but cannot create, alter, issue, or void it.

Messaging, calling, notifications, audit events, and access controls join these workflows. They are not decorative dashboard widgets; they persist state in the backend and expose real delivery, seen, call, and read statuses.

## A.2 Product goals

- Make urgent and due work visible to the correct person.
- Preserve a traceable longitudinal patient record.
- Prevent cross-patient and cross-role information leakage.
- Minimize duplicate entry and disconnected workflow states.
- Keep clinical decisions explainable and configurable.
- Run locally with SQLite and no separate database server.
- Remain understandable and maintainable by another engineering team.

## A.3 Explicit non-goals for the first release

- Multi-tenancy, subscriptions, or SaaS organization management.
- Patient self-service accounts; the external role is Patient Guard.
- AI-generated diagnoses, opaque transfer ranking, or hard-coded clinical thresholds.
- Pharmacy inventory, laboratory information systems, radiology/PACS, insurance claims, or full payroll.
- Emergency “break-glass” access until the hospital supplies an approval and review policy.
- Editing already signed clinical notes or already issued certificates without a formal amendment/void event.
- Claiming regulatory certification. The design follows privacy and audit principles, but legal compliance requires jurisdiction-specific review, deployment controls, policy, and training.

---

# B. Technical architecture

## B.1 System context

```text
Browser / Tablet
  React application
  ├── HTTPS REST requests
  └── Authenticated WebSocket events
            │
            ▼
Django ASGI application
  ├── Django REST Framework API
  ├── Session authentication + CSRF
  ├── RBAC and object-level policies
  ├── Domain services and selectors
  ├── WebSocket consumers
  ├── Scheduler management worker
  └── Integration adapters
            │
            ▼
Django ORM
            │
            ▼
SQLite database + protected local media storage

External adapters (only when configured): SMTP and Twilio
```

The browser never talks directly to SQLite, SMTP, or Twilio secrets. The frontend calls same-origin `/api/v1/` endpoints; Vite proxies those paths to Django during development. All durable actions are committed in Django before the UI treats them as successful.

## B.2 Frontend responsibilities

- Render role-specific routes and action-focused dashboards.
- Enforce route visibility for usability, while treating backend permissions as authoritative.
- Fetch and mutate server state through typed feature APIs and TanStack Query.
- Validate forms client-side for immediate feedback, then render backend field and workflow errors.
- Maintain access-token-free session state through `/auth/session/`.
- Receive WebSocket events and invalidate the relevant REST queries; never use transient events as the source of truth.
- Provide loading, skeleton, empty, partial-error, forbidden, not-found, and offline/retry states.
- Avoid displaying sensitive data in URLs, browser storage, analytics, or client logs.

## B.3 Backend responsibilities and layering

Each backend domain uses the following boundaries:

1. **API serializers** validate transport shape and convert it to explicit service inputs.
2. **Permissions/policies** verify role-level capability.
3. **Selectors** return already-scoped querysets for the requesting user.
4. **Services/use cases** enforce cross-model invariants, status transitions, transactions, audit records, and notification events.
5. **Models** enforce durable constraints, field validity, uniqueness, and indexes.
6. **Integration adapters** isolate SMTP and Twilio provider code.
7. **API views** remain thin; they do not contain recommendation, scheduling, or clinical-analysis logic.

Mutating workflows use `transaction.atomic`. Actions that can be retried accept an idempotency key or enforce a natural unique constraint. External delivery occurs after the clinical transaction through an outbox record so an SMTP/Twilio outage cannot roll back valid hospital data.

## B.4 Authentication and session security

- Email is the login identifier; public self-registration is disabled.
- Admin creates initial Head of Service, Admin, and Accounting accounts. Head of Service invites Doctor/Nurse staff. An assigned Nurse invites a Patient Guard in the context of a patient.
- Invitations use a random, expiring, one-time token. Only its hash is stored.
- Passwords use Django's password framework with Argon2 preferred.
- Login creates a server-side Django session in an `HttpOnly`, `Secure` in production, `SameSite=Lax` cookie.
- Mutating requests require a CSRF token. Login, refresh/session checks, and logout follow the same-origin CSRF policy.
- Session expiry, failed-login throttling, account deactivation, password reset, and forced password change are implemented centrally.
- CORS is closed by default; deployed frontend origins are explicit. WebSockets enforce allowed origins and session authentication.
- Twilio capability tokens are short-lived and issued only to an authenticated user eligible to join that call.

Session authentication is selected over local-storage JWTs because this is a browser-first, same-origin hospital application and server-side revocation is important. A future mobile client can add a separate token flow without weakening the browser baseline.

## B.5 Authorization model

Every protected request passes all applicable gates:

```text
Authenticated user
  → active account
  → role capability
  → scoped queryset/object policy
  → relationship to this patient
  → field/release visibility
  → valid workflow transition
  → audit event for sensitive access or mutation
```

Patient access is based on current data, not a client-supplied role claim:

- A Doctor or Nurse needs an active care-team assignment to that patient.
- A Patient Guard needs an active `GuardianAccess` link to that patient and the relevant permission flag.
- Accounting receives demographics and billing scope only.
- Head of Service receives hospital operations scope, not blanket clinical-record access.
- Admin receives identity/system scope, not blanket clinical-record access.
- API detail endpoints first use a user-scoped selector, so guessing a UUID returns no protected object.

Frontend route guards improve navigation but never substitute for these backend checks.

## B.6 SQLite strategy

SQLite is retained as required. The implementation will use:

- Django migrations for every schema change.
- Foreign keys, check constraints, conditional unique constraints where supported, and explicit indexes.
- WAL mode, a reasonable busy timeout, short transactions, and no network-mounted database file.
- Decimal fields for measurements and money rather than binary floating point.
- UTC timestamps in the database and the hospital's configured timezone at the presentation/scheduling boundary.
- Encrypted transport, restricted filesystem permissions, encrypted host volumes/backups, and tested backup/restore procedures.
- A single primary ASGI application process plus controlled scheduler worker for the initial deployment, consistent with SQLite's write-concurrency profile.

SQLite is suitable for local operation and a controlled single-hospital deployment, but it is not a horizontally scalable write store. This architecture does not hide that constraint. A database migration would require explicit future approval and is not part of this design.

## B.7 Real-time and scheduled behavior

**Messaging and notifications:** REST creates the durable message/notification and receipt rows. After commit, an authenticated WebSocket event tells connected clients which query to refresh. Reconnect performs REST synchronization using the last seen timestamp/cursor, so events cannot be lost permanently.

**Medication alerts and missed doses:** An idempotent Django management worker scans due `MedicationDose` rows on a short interval. Unique deduplication keys prevent duplicate alerts. Hospital policy defines how long after the scheduled time a still-pending dose becomes `MISSED`; no timing rule is hard-coded without configuration.

**Retries:** The same worker processes pending outbox/email records with bounded retries. It records the attempt and last error. Clinical transactions never pretend an email was sent before the provider confirms success.

## B.8 File and sensitive-data handling

- Uploaded documents and generated certificates live outside the public static tree.
- Django authorizes every download and streams it with safe content headers.
- Metadata, SHA-256 checksum, uploader, MIME type, size, and audit events are stored in SQLite.
- Filenames are generated; user-provided names are display metadata only.
- Transfer packages are generated from an allowlisted record set, not from unrestricted database serialization.
- Logs redact passwords, session IDs, invitation tokens, health-record bodies, and integration secrets.

---

# C. Final frontend folder structure

The frontend uses role-oriented modules because the same clinical object has different actions for different users. Cross-role products such as messaging are centralized only where the workflow truly is shared.

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   ├── route-paths.ts
│   │   ├── providers/
│   │   │   ├── AppProviders.tsx
│   │   │   ├── QueryProvider.tsx
│   │   │   └── RealtimeProvider.tsx
│   │   ├── guards/
│   │   │   ├── RequireSession.tsx
│   │   │   ├── RequireRole.tsx
│   │   │   └── RequireCapability.tsx
│   │   ├── layouts/
│   │   │   ├── AuthLayout.tsx
│   │   │   ├── HospitalShell.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Topbar.tsx
│   │   │   └── MobileNavigation.tsx
│   │   └── error-boundaries/
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   ├── invitation-acceptance/
│   │   │   ├── password-reset/
│   │   │   └── session/
│   │   ├── head-of-service/
│   │   │   ├── dashboard/
│   │   │   ├── medical-personnel/
│   │   │   ├── hospital-information/
│   │   │   ├── departments/
│   │   │   ├── specialties/
│   │   │   ├── clinical-rules/
│   │   │   ├── resources/
│   │   │   ├── rooms-and-beds/
│   │   │   ├── services/
│   │   │   ├── external-hospitals/
│   │   │   └── reports/
│   │   ├── doctor/
│   │   │   ├── dashboard/
│   │   │   ├── patients/
│   │   │   │   ├── patient-list/
│   │   │   │   ├── patient-registration/
│   │   │   │   ├── patient-details/
│   │   │   │   └── care-team/
│   │   │   ├── medical-files/
│   │   │   ├── monitoring/
│   │   │   ├── prescriptions/
│   │   │   ├── transfers/
│   │   │   └── death-certificates/
│   │   ├── nurse/
│   │   │   ├── dashboard/
│   │   │   ├── assigned-patients/
│   │   │   ├── patient-guards/
│   │   │   ├── vital-signs/
│   │   │   ├── medication/
│   │   │   └── alerts/
│   │   ├── patient-guard/
│   │   │   ├── dashboard/
│   │   │   ├── patient-information/
│   │   │   ├── medical-file/
│   │   │   ├── prescriptions/
│   │   │   ├── monitoring/
│   │   │   ├── transfers/
│   │   │   └── death-certificates/
│   │   ├── accounting/
│   │   │   ├── dashboard/
│   │   │   ├── invoices/
│   │   │   ├── charges/
│   │   │   ├── payments/
│   │   │   └── reports/
│   │   ├── admin/
│   │   │   ├── dashboard/
│   │   │   ├── users/
│   │   │   ├── system-health/
│   │   │   ├── integrations/
│   │   │   └── audit/
│   │   ├── communication/
│   │   │   ├── conversations/
│   │   │   ├── messages/
│   │   │   └── calls/
│   │   ├── notifications/
│   │   └── profile/
│   ├── shared/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── csrf.ts
│   │   │   ├── errors.ts
│   │   │   └── pagination.ts
│   │   ├── ui/
│   │   │   ├── actions/
│   │   │   ├── data-display/
│   │   │   ├── feedback/
│   │   │   ├── forms/
│   │   │   ├── navigation/
│   │   │   └── overlays/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   ├── accessibility/
│   │   └── styles/
│   │       ├── tokens.css
│   │       ├── globals.css
│   │       └── print.css
│   ├── assets/
│   ├── test/
│   │   ├── factories/
│   │   ├── handlers/
│   │   └── setup.ts
│   └── main.tsx
├── e2e/
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Feature ownership rule

A feature creates only the subfolders it needs: typically `pages`, `components`, `api`, `hooks`, `schemas`, `types`, and `tests`. A two-file feature is not expanded into empty architecture. UI components enter `shared/ui` only when they are business-agnostic and reused by multiple domains.

`communication`, `notifications`, and `profile` are intentionally cross-role modules. Their backend object policies vary results by user; duplicating five message implementations would be less secure and less maintainable. Doctor prescription authoring, Nurse administration, and Guard prescription reading remain separate because their workflows and permissions differ.

---

# D. Final backend folder structure

```text
backend/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── websocket.py
├── apps/
│   ├── common/
│   │   ├── models.py
│   │   ├── exceptions.py
│   │   ├── pagination.py
│   │   ├── request_ids.py
│   │   └── validators.py
│   ├── identity/
│   ├── hospital/
│   ├── patients/
│   ├── clinical_records/
│   ├── vital_signs/
│   ├── prescriptions/
│   ├── monitoring/
│   ├── transfers/
│   ├── death_certificates/
│   ├── messaging/
│   ├── calls/
│   ├── notifications/
│   ├── billing/
│   ├── reports/
│   └── audit/
├── integrations/
│   ├── email/
│   │   ├── client.py
│   │   ├── transfer_package.py
│   │   └── templates/
│   └── twilio/
│       ├── client.py
│       ├── tokens.py
│       └── webhooks.py
├── templates/
├── locale/
├── media/                 # deployment-mounted; never public/static
├── scripts/
├── tests/
│   ├── workflows/
│   ├── permissions/
│   └── contract/
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── pyproject.toml
```

A substantial domain app follows this internal pattern:

```text
apps/<domain>/
├── models/
│   ├── __init__.py
│   └── <cohesive_model_group>.py
├── api/
│   ├── serializers/
│   ├── views/
│   └── urls.py
├── services/
├── selectors/
├── permissions.py
├── events.py
├── admin.py
├── migrations/
└── tests/
```

Rules:

- No global catch-all `services.py` or giant `models.py`.
- Cross-domain imports point toward stable identities and service interfaces; they do not create circular model logic.
- `common` contains technical primitives only, never patient business rules.
- Django admin is restricted to technical recovery/reference configuration. It does not bypass application patient-access policy for ordinary users.
- Domain status changes happen in service functions, not arbitrary serializer updates.

---

# E. Database model design

## E.1 Modeling conventions

Unless stated otherwise, entities have a UUID primary key, `created_at`, and `updated_at`. Important records also store `created_by`. Enumerated states use `TextChoices`; money and measurements use `DecimalField`; all timestamps are timezone-aware. Clinical and financial rows are archived, voided, or superseded rather than physically deleted.

JSON is limited to provider payloads, immutable snapshots, typed answer values, and explainability details. Core relationships remain relational and indexable.

## E.2 Identity and access

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `User` | email, first_name, last_name, phone, role, is_active, must_change_password, last_login | Custom Django user. Email unique. One primary role from `ADMIN`, `HEAD_OF_SERVICE`, `DOCTOR`, `NURSE`, `PATIENT_GUARD`, `ACCOUNTING`. |
| `StaffProfile` | employee_number, job_title, license_number, hire_date, employment_status | One-to-one `User`; optional Department. Required for hospital staff roles, not Patient Guard. Employee number unique. |
| `StaffSpecialty` | is_primary, verified_at | StaffProfile ↔ Specialty many-to-many. Service validates Doctor/qualified staff role. |
| `PatientGuardProfile` | address, preferred_language, preferred_contact_method | One-to-one User whose role is Patient Guard. |
| `Invitation` | email, intended_role, token_hash, expires_at, accepted_at, revoked_at | Invited by User; optional patient context and pending GuardianAccess. Token hash unique and token is one-use. |
| `LoginEvent` | outcome, ip_address, user_agent, occurred_at | Optional User; security audit without storing password/session content. |

Django's session model is used for authenticated sessions. Users are deactivated, not deleted, when referenced by medical history.

## E.3 Hospital configuration and transfer directory

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `HospitalProfile` | legal_name, display_name, registration_number, address, city, country, email, phone, timezone | Singleton enforced by service/database convention. Contains no integration secret. |
| `Department` | code, name, description, location, phone, is_active | Optional parent department and optional Head of Service/department head. Code unique. |
| `Specialty` | code, name, description, is_active | Referenced by staff, conditions, transfers, and hospitals. |
| `ClinicalCondition` | coding_system, code, name, description, is_active | Unique coding-system/code pair; local codes are permitted. |
| `SpecialtyCondition` | match_weight, notes | Specialty ↔ ClinicalCondition mapping used by explainable recommendations. Unique pair. |
| `ServiceDefinition` | code, name, category, description, is_active | Shared service vocabulary. |
| `HospitalServiceAvailability` | availability_status, notes | ServiceDefinition + Department; unique active pair. |
| `Room` | code, floor, room_type, status | Belongs to Department. Code unique. |
| `Bed` | code, status | Belongs to Room. Unique room/code; current occupancy derived from BedAssignment. |
| `Resource` | asset_code, name, category, quantity_total, quantity_available, status, notes | Belongs to Department; equipment/supply/other operational resources. Check available ≤ total. |
| `ExternalHospital` | name, address, city, country, latitude, longitude, email, phone, transfer_email, is_active, notes | Destination directory. Transfer email is required before transmission, not necessarily at draft creation. |
| `ExternalHospitalSpecialty` | availability_status, notes | ExternalHospital ↔ Specialty; unique pair. |
| `ExternalSpecialist` | full_name, title, phone, email, is_active | ExternalHospital + Specialty. Contact details are optional and separately maintainable. |
| `ExternalHospitalService` | availability_status, notes | ExternalHospital ↔ ServiceDefinition; unique pair. |

## E.4 Patient identity, access, and episodes

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `Patient` | medical_record_number, first_name, last_name, date_of_birth, sex_at_birth, gender_identity, blood_type, phone, email, address, emergency_contact_name/phone, status | Registered by User. MRN unique. Status includes registered, admitted, discharged, transferred, deceased, archived. |
| `CareEpisode` | episode_number, episode_type, admission_reason, admitted_at, discharged_at, status | Patient + Department. Represents inpatient, outpatient, or emergency care. Episode number unique. |
| `PatientCareAssignment` | assignment_type, is_primary, starts_at, ends_at | Patient, optional CareEpisode, and StaffProfile; assigned_by User. Assignment type Doctor/Nurse must match staff role. Only one active primary assignment per type/episode. |
| `GuardianAccess` | relationship, status, can_view_medical_file, can_answer_monitoring, can_decide_transfers, can_view_billing, granted_at, revoked_at | Patient + PatientGuardProfile; granted/revoked by authorized User. Prevents implicit access from role alone. |
| `BedAssignment` | starts_at, ends_at | Bed + Patient + CareEpisode; assigned_by User. Prevent overlapping active occupancy for a bed. |

## E.5 Clinical record

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `MedicalFile` | file_number, status, opened_at | One-to-one Patient; opened by Doctor during registration. |
| `Allergy` | substance, reaction, severity, status, recorded_at | Patient; recorded_by authorized clinician. |
| `MedicalHistoryEntry` | category, title, occurred_on, description, source, guardian_visibility | Patient/MedicalFile; recorded_by clinician. |
| `Diagnosis` | code_snapshot, name_snapshot, description, diagnosis_status, diagnosed_at, guardian_visibility | Patient, optional CareEpisode and ClinicalCondition; diagnosed_by Doctor. |
| `TreatmentPlan` | title, objectives, instructions, status, starts_on, ends_on, guardian_visibility | Patient, optional CareEpisode; authored_by Doctor. |
| `ClinicalNote` | note_type, body, status, signed_at, guardian_visibility | Patient/CareEpisode; authored_by User; optional `amends` self-reference. Signed notes are immutable and amended through a new row. |
| `MedicalDocument` | document_type, storage_key, original_name, mime_type, byte_size, checksum, status, guardian_visibility | Patient/MedicalFile; uploaded_by User. File bytes are outside the public static directory. |

Guardian visibility never overrides an inactive GuardianAccess link. Prescription and issued-certificate visibility are governed by their own workflow states.

## E.6 Vital signs and configurable analysis

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `VitalMetric` | code, name, unit, decimal_places, is_active | Metric vocabulary only; contains no invented threshold. Code unique. |
| `VitalRuleSet` | name, version, status, effective_from, effective_to, approved_at | Approved_by authorized Head of Service. One active ruleset for a given effective time. Draft changes create a new version. |
| `VitalRule` | name, operator, lower_value, upper_value, result_status, priority, explanation_template, is_active | RuleSet + VitalMetric. Operator determines which threshold fields are required. Initially rules identify critical values; absence of a matching rule is stable only when an active complete ruleset exists. |
| `VitalObservation` | observed_at, status, notes, analyzed_at, ruleset_name/version snapshot | Patient, optional CareEpisode; recorded_by assigned Nurse. Status: unassessed, stable, critical. |
| `VitalValue` | value | Observation + VitalMetric; unique metric per observation. |
| `VitalRuleEvaluation` | matched, result_status, measured_value, rule_snapshot, explanation | Observation + VitalValue + VitalRule. Preserves why the historical classification occurred after rules change. |

No default threshold values will be seeded unless approved clinical values are supplied by the hospital.

## E.7 Prescriptions and medication administration

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `Medication` | generic_name, brand_name, form, strength, is_active | Hospital medication vocabulary. No inventory behavior in first release. |
| `Prescription` | status, prescribed_at, starts_on, ends_on, clinical_instructions | Patient/CareEpisode; prescribed_by assigned Doctor. Draft, active, completed, cancelled. |
| `PrescriptionItem` | dose_amount, dose_unit, route, frequency_display, duration_days, instructions, schedule_type, prn_max_per_day | Prescription + Medication. Scheduled or as-needed (PRN). |
| `DoseScheduleRule` | starts_on, ends_on, local_time, days_of_week, timezone | PrescriptionItem. Structured input used to generate due doses; no free-text parser makes clinical assumptions. |
| `MedicationDose` | scheduled_for, status, actual_at, notes | PrescriptionItem; assigned patient is derived. Nurse set when administered/refused/missed. Unique item/scheduled time. States: pending, administered, missed, refused, cancelled. |
| `MedicationDoseEvent` | event_type, previous_status, new_status, occurred_at, notes | MedicationDose + acting Nurse/User. Append-only history for every state change. |

Activation generates the schedule transactionally. Editing an active prescription cancels future affected doses and creates an auditable revision instead of silently rewriting administration history.

## E.8 Monitoring conversation

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `MonitoringThread` | subject, status, opened_at, closed_at | Patient + assigned Doctor + designated PatientGuardProfile. |
| `MonitoringQuestion` | prompt, response_type, options, sequence, asked_at, due_at, status | Belongs to MonitoringThread. Types: yes/no, text, number, single choice. |
| `MonitoringResponse` | answer, submitted_at | Question + responding Patient Guard; optional `supersedes` response. Answer shape validated against question type. Historical rows are not overwritten. |

## E.9 Transfer and explainable recommendations

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `TransferRequest` | reason, clinical_summary, urgency, status, submitted_at, decided_at, transmitted_at, version | Patient/CareEpisode; requested_by Doctor; designated decision_guardian; selected ExternalHospital optional until submission. |
| `TransferRequirement` | requirement_type, weight, is_mandatory, label_snapshot | TransferRequest plus exactly one Specialty, ServiceDefinition, or ClinicalCondition according to type. |
| `TransferRecommendation` | score, rank, matched_requirements, missing_requirements, explanation, generated_at, rules_version | TransferRequest + ExternalHospital. Snapshot is regenerated explicitly, never silently changed. Unique request/hospital per generation. |
| `TransferDecision` | decision, reason, decided_at | One-to-one TransferRequest + designated Patient Guard. Approve or reject; replacement requires explicit reopen workflow. |
| `TransferStatusEvent` | previous_status, new_status, reason, occurred_at | TransferRequest + actor; append-only transition history. |
| `TransferTransmission` | recipient_email, package_storage_key, checksum, status, attempts, last_error, sent_at | Approved TransferRequest + ExternalHospital; initiated_by Doctor. Tracks SMTP result and generated package. |

Recommended status flow:

`DRAFT → RECOMMENDED → PENDING_GUARDIAN → APPROVED | REJECTED → FILE_SENT → COMPLETED`

Cancellation is permitted from defined pre-completion states and always requires a reason.

## E.10 Death certificates

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `DeathCertificate` | certificate_number, death_datetime, place_of_death, primary_cause, contributing_causes, manner_of_death, notes, status, issued_at, voided_at, void_reason, pdf_storage_key, checksum | Patient + issuing Doctor. Draft, issued, void. Only one current issued certificate per patient; a correction voids and reissues rather than edits. |

The exact legal fields and numbering policy require jurisdictional confirmation before implementation.

## E.11 Messaging and calling

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `Conversation` | conversation_type, subject, is_active | Created_by User; optional patient context. Patient context does not itself grant record access. |
| `ConversationParticipant` | joined_at, left_at, is_muted | Conversation + User; unique active membership. Membership creation validates that users are allowed to communicate in context. |
| `Message` | message_type, body, sent_at, client_message_id | Conversation + sender; optional reply_to Message. Client ID gives idempotency. Clinical messages are not hard-deleted. |
| `MessageAttachment` | storage_key, original_name, mime_type, byte_size, checksum | Message; every download is authorized and audited. |
| `MessageReceipt` | delivered_at, seen_at | Message + recipient User. Created for every recipient other than sender. `seen_at` implies delivered. |
| `CallSession` | provider, provider_sid, direction, status, initiated_at, ringing_at, answered_at, ended_at, failure_reason | Initiated_by User; optional Conversation and patient context. |
| `CallParticipant` | provider_identity, status, joined_at, left_at | CallSession + User. |
| `CallWebhookEvent` | provider_event_id, event_type, payload_hash, received_at, processed_at, processing_error | Optional CallSession. Unique provider event makes webhook processing idempotent. Raw sensitive provider payload is not retained unnecessarily. |

Call states include queued, ringing, in progress, completed, declined, no answer, failed, and cancelled. If Twilio is not configured, call initiation returns a clear integration-unavailable result and the UI does not fake a call.

## E.12 Notifications, reliable delivery, and preferences

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `Notification` | category, severity, title, body, route, data, dedupe_key, created_at, delivered_at, read_at, archived_at | Recipient User; optional actor and patient. Unique recipient/dedupe key where present. |
| `NotificationPreference` | category, in_app_enabled, email_enabled | User/category unique. Safety-critical in-app alerts cannot be disabled by ordinary users. |
| `OutboxEvent` | topic, aggregate_type, aggregate_id, payload, status, available_at, attempts, last_error, processed_at | Reliable post-commit work for WebSocket, email, and integration side effects. |
| `EmailDelivery` | purpose, recipient_email, template_name, related_type/id, status, attempts, provider_message_id, last_error, sent_at | Generic invitation and notification email audit. Transfer email retains its richer TransferTransmission record. |

## E.13 Billing and reporting

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `ChargeItem` | code, name, category, default_unit_price, is_active | Billing catalogue. Code unique. |
| `Invoice` | invoice_number, status, issued_at, due_at, subtotal, adjustments, total, amount_paid | Patient + optional CareEpisode; created_by Accounting. Financial snapshots do not change when catalogue prices change. |
| `InvoiceLine` | description, quantity, unit_price, line_total, service_date | Invoice + optional ChargeItem. |
| `Payment` | receipt_number, amount, method, reference, received_at, status | Invoice; recorded_by Accounting. Reversals are explicit records/status transitions. |
| `ReportExport` | report_type, filters, status, storage_key, checksum, generated_at, expires_at | Requested_by authorized User. Report selectors apply the requester's data scope. |

## E.14 Audit and medical-record access

| Model | Principal attributes | Relationships and constraints |
|---|---|---|
| `AuditEvent` | action, object_type, object_id, before_snapshot, after_snapshot, reason, request_id, ip_address, user_agent, occurred_at | Actor User and optional Patient. Append-only; sensitive values are redacted. |
| `MedicalRecordAccess` | object_type, object_id, action, purpose, request_id, occurred_at | User + Patient. Records view, print, download, and transmit access. |

## E.15 High-level relationship map

```text
User ──1:1── StaffProfile ──M:N── Specialty
  │
  ├── PatientCareAssignment ── Patient ──1:1── MedicalFile
  │                                  ├── CareEpisode ── BedAssignment
  │                                  ├── Clinical records
  │                                  ├── VitalObservation ── VitalValue
  │                                  ├── Prescription ── Item ── MedicationDose
  │                                  ├── MonitoringThread ── Question ── Response
  │                                  ├── TransferRequest ── Recommendation ── ExternalHospital
  │                                  └── DeathCertificate
  │
  └── PatientGuardProfile ── GuardianAccess ── Patient

Conversation ── Participant(User)
             └── Message ── Receipt(User)

Notification ── recipient(User), optional Patient
AuditEvent / MedicalRecordAccess ── User, optional Patient
Invoice ── Patient ── Payment
```

---

# F. Role-permission matrix

Legend: **Manage** = create/read/update through valid transitions; **Scoped** = only explicitly related patients/records; **Read** = read-only; **None** = denied by default.

| Capability | Admin | Head of Service | Doctor | Nurse | Patient Guard | Accounting |
|---|---|---|---|---|---|---|
| Own profile/password | Manage | Manage | Manage | Manage | Manage | Manage |
| System roles and initial privileged accounts | Manage | None | None | None | None | None |
| Create/invite Doctor and Nurse | Read/audit | Manage | None | None | None | None |
| Create/invite Patient Guard | Audit | Read relationship | None | Manage for assigned patient | Accept own invite | None |
| Departments, specialties, services | Technical support only | Manage | Read | Read | None | Read limited labels |
| Clinical vital rule sets | No clinical edits | Manage/version/approve | Read | Read applicable | None | None |
| Rooms, beds, operational resources | Technical support only | Manage | Read availability | Read/update assigned operations | None | Billing-related read |
| External hospitals/capabilities | Technical support only | Manage | Read/select | Read | Read selected destination | None |
| Register patient | None | Operational aggregate only | Manage | None | None | None |
| Assign/reassign care team | None | Operational oversight | Manage Doctor/Nurse assignment under policy | None | None | None |
| View patient demographics | None by default | Aggregate only | Scoped | Scoped | Scoped own link | Scoped billing identity |
| View clinical medical file | None by default | None by default | Scoped full clinical | Scoped care-relevant | Scoped released fields only | None |
| Add diagnosis/treatment/signed note | None | None | Scoped Manage | Nursing note only; no diagnosis | None | None |
| Record vital observations | None | Configuration/aggregate only | Read scoped | Scoped Manage | Read released summary only if allowed | None |
| Prescribe/cancel medication | None | None | Scoped Manage | Read scoped | Read active scoped | None |
| Administer/refuse/miss dose | None | None | Read outcomes | Scoped Manage | Read authorized schedule/outcome | None |
| Create monitoring questions | None | None | Scoped Manage | Read care-relevant | None | None |
| Answer monitoring question | None | None | Read responses | Read care-relevant | Scoped Manage as designated guard | None |
| Create/select/submit transfer | None | Read operational state | Scoped Manage | Read care-relevant | None | None |
| Approve/reject transfer | None | None | Read decision | Read care-relevant | Scoped designated decision only | None |
| Send transfer medical package | None | Delivery aggregate only | Scoped, approved requests only | None | Read state | None |
| Create/issue/void death certificate | None | None | Scoped Manage | None | None | None |
| View/print death certificate | None | None | Scoped | Care-relevant read | Scoped issued certificate | None |
| Messaging | Scoped by membership | Scoped by membership | Scoped by membership | Scoped by membership | Scoped by membership | Scoped by membership |
| Calling | Scoped eligible contacts | Scoped eligible contacts | Scoped eligible contacts | Scoped eligible contacts | Scoped eligible contacts | Scoped eligible contacts |
| Notifications | Own | Own | Own | Own | Own | Own |
| Billing/charges/payments | Technical support only | Aggregate reports | None | None | Optional read if GuardianAccess permits | Manage |
| Clinical reports | None | De-identified/aggregate operational only | Scoped | Scoped care reports | None | None |
| Financial reports | Technical support only | Aggregate if policy allows | None | None | None | Manage |
| Audit logs | System/security audit; clinical content redacted | Staff/config audit | Own relevant events | Own relevant events | Own access/activity | Financial audit |

### Critical “cannot” rules

- Admin and Head of Service do **not** automatically receive medical-record access.
- Doctor cannot access patients without an active care assignment and cannot answer on behalf of a Patient Guard.
- Nurse cannot diagnose, prescribe, approve transfers, or issue death certificates.
- Patient Guard cannot discover unlinked patients, see internal clinical notes, alter prescriptions, administer medication, or create/edit certificates.
- Accounting cannot read diagnoses, vital signs, prescriptions, monitoring answers, or transfer clinical summaries.
- No role may skip a required status transition by sending an arbitrary `status` field.
- No user may add themselves to a care assignment, guardian link, or conversation to gain access.

---

# G. API structure

## G.1 API conventions

- Base path: `/api/v1/`
- JSON over HTTPS; multipart only for authorized uploads.
- UUIDs in URLs; sensitive names/details do not appear in query strings.
- Cursor pagination for messages/notifications and page pagination for administrative tables.
- Search, ordering, and filters are explicit allowlists.
- Mutations return the persisted representation and relevant workflow metadata.
- Errors use a stable envelope with an error code, human-safe message, field errors, and request ID.
- `400` validation, `401` unauthenticated, `403` authenticated but forbidden, `404` absent or outside object scope, `409` duplicate/invalid transition/version conflict, `422` semantically invalid request when appropriate, and `503` integration unavailable.
- Idempotency keys apply to patient registration, message send, medication confirmation, transfer submission/transmission, payments, and call initiation.

## G.2 Endpoint groups and responsibilities

### Authentication and identity — `/auth`, `/users`, `/staff`

- Session/CSRF bootstrap, login, logout, current session, password change/reset.
- Invitation acceptance and expiry/revocation.
- Admin-managed privileged users.
- Head-of-Service staff list, invite, deactivate, department assignment, and specialty assignment.
- Never return password hashes, token hashes, or unrestricted user directories.

### Hospital configuration — `/hospital`

- Hospital profile.
- Departments, specialties, conditions and mappings.
- Services and availability.
- Rooms, beds, bed assignments, and resources.
- External hospitals, external specialties, specialists, and services.
- Vital rules are exposed under `/vital-rule-sets` with draft, validate, approve, activate, and retire actions.

### Patients and access — `/patients`

- Scoped patient list/detail, registration, archive, and demographics update.
- Care episodes and care-team assignments.
- Guardian invitations/access, permission changes, and revocation.
- Nested paths are used for context; policy still validates the patient relationship.

### Clinical records — `/medical-files`

- Scoped medical-file summary and timeline.
- Allergies, history, diagnoses, treatment plans, clinical notes, and documents.
- Explicit sign/amend/release actions where applicable.
- Authorized document stream/download endpoint with access logging.

### Vitals — `/vital-observations`, `/vital-metrics`

- Nurse creates an observation with one or more metric values.
- Read observation history and trend series within patient scope.
- The create response includes classification and human-readable rule evaluation.
- Reanalysis is a privileged explicit action that preserves both prior and new analysis history; routine rule changes do not rewrite old results.

### Prescriptions and medication — `/prescriptions`, `/medication-doses`

- Doctor drafts, revises, activates, completes, or cancels prescription through action endpoints.
- Role-specific scoped list/detail representations.
- Nurse due/overdue queue.
- Administer, refuse, and mark-missed actions with transition checks and actual timestamp.
- Dose history for Doctor/Nurse and authorized Guard views.

### Monitoring — `/monitoring`

- Doctor creates/closes thread and adds questions.
- Designated Guard lists pending questions and submits typed responses.
- Doctor lists unread/new responses and full history.

### Transfers — `/transfers`

- Doctor creates requirements and requests recommendation generation.
- Recommendation response includes score, matched/missing criteria, rank, and data timestamp.
- Doctor selects destination and submits to designated Guard.
- Guard approve/reject actions.
- Doctor transmit action only for approved request and eligible selected hospital.
- Transmission attempts and status are read-only audit views.

### Death certificates — `/death-certificates`

- Doctor draft, issue, and void/reissue actions.
- Guard list/detail includes issued certificates only.
- Authorized print/PDF endpoint logs access.

### Messaging — `/conversations`, `/messages`, WebSocket `/ws/events`

- Eligible conversation creation and participant listing.
- Cursor-based message history and idempotent send.
- Delivered and seen receipt actions, preferably batched to the latest message.
- WebSocket pushes message/receipt identifiers; REST remains authoritative.

### Calls — `/calls`, `/integrations/twilio/webhooks`

- Eligible call initiation, short-lived Twilio client token, call detail/history, decline/end actions.
- Signed Twilio voice/status webhooks update `CallSession` and participants idempotently.
- Provider availability endpoint lets UI disable calling with an explanation.
- WebRTC calls ring app-wide: a global call overlay (mounted in the application shell, not on the `/calls` page) surfaces incoming calls on any route, with a background poll as a safety net when the realtime socket is unavailable.
- WebRTC offers/answers are persisted on `CallSession` (`offer_sdp`/`offer_from`, `answer_sdp`/`answer_from`) when relayed through `POST /calls/{id}/signal/`, so a participant who missed the realtime delivery (different page, reconnecting socket) recovers the signal from `GET /calls/{id}/` when accepting or connecting instead of failing.
- One active call per participant: initiating while either side is already in a `QUEUED`/`RINGING`/`IN_PROGRESS` session is rejected with `409 call_busy`. Two people calling each other at the same moment are serialized (user-row locks, stable order) — the earlier session wins and the later caller gets a busy message, WhatsApp-style.

### Notifications — `/notifications`

- Own notification list, unread count, mark read, mark all read, archive, and preferences.
- Critical categories remain enabled in-app.

### Billing and reports — `/billing`, `/reports`

- Accounting-scoped charge catalogue, invoices, lines, payment recording/reversal, and receipts.
- Role-scoped report summaries and asynchronous exports.
- Patient Guard billing visibility only when explicitly granted and later approved as product scope.

### Audit/system health — `/audit`, `/system`

- Admin security/configuration audit with sensitive fields redacted.
- User-visible “my activity” where appropriate.
- SMTP/Twilio configuration presence and last health state, never credentials.

---

# H. Complete workflow map

## H.1 Staff onboarding and hospital setup

```text
Admin creates initial Head of Service
  → Head of Service configures hospital, departments, specialties and services
  → Head of Service configures rooms/beds/resources and external hospitals
  → Head of Service invites Doctor/Nurse with role and department
  → Staff accepts expiring invitation and sets password
  → Account activation + audit event + welcome notification
```

## H.2 Patient intake and Guard association

```text
Assigned/authorized Doctor submits patient + active Nurse
  → validate Doctor and Nurse roles/status
  → one transaction creates Patient, MedicalFile, CareEpisode and assignments
  → assignment notification to Nurse
  → Nurse opens only an assigned patient
  → Nurse creates Guard invitation + pending GuardianAccess
  → Guard accepts and account/link become active
  → Doctor and Nurse are notified that Guard access exists
```

Duplicate MRN/contact checks produce a conflict for human resolution rather than silently creating duplicate patients.

## H.3 Vitals and critical alert

```text
Nurse opens assigned patient
  → submits observed time + metric values
  → server validates active assignment and metric definitions
  → evaluation service loads effective approved rule set
  → stores observation, values and every rule evaluation
  → sets UNASSESSED, STABLE or CRITICAL with explanation
  → if CRITICAL, creates deduplicated high-severity notification for active Doctor(s)
  → WebSocket prompts dashboard refresh
  → Doctor opens alert and medical-file timeline
  → access and acknowledgement are audited
```

If no approved rule set can assess the values, status is **Unassessed**, never falsely “Stable.”

## H.4 Prescription and medication loop

```text
Doctor creates draft Prescription + items + schedule rules
  → activation validates dates and structured schedule
  → future MedicationDose rows are generated
  → Guard can view active prescription
  → assigned Nurse sees upcoming/due queue
  → scheduler creates due alert once
  → Nurse chooses Administered, Refused, or Missed with notes as required
  → Dose current state + append-only event are saved atomically
  → Doctor sees outcome; configured exceptional outcomes create alerts
```

Concurrent confirmation of the same dose produces a conflict instead of two administrations.

## H.5 Monitoring conversation

```text
Doctor creates patient-scoped thread for designated Guard
  → adds typed question(s) and due time
  → Guard receives notification
  → Guard submits response validated against question type
  → prior response is preserved if correction is allowed
  → Doctor receives response notification
  → Doctor adds follow-up question or closes thread
```

## H.6 Explainable transfer

```text
Doctor creates TransferRequest and clinical requirements
  → recommendation service filters active external hospitals
  → mandatory criteria determine eligibility
  → weighted specialty/service matches determine score
  → result stores rank + matched/missing reasons + source-data timestamp
  → Doctor reviews details and selects hospital
  → Doctor submits to one authorized decision Guard
  → Guard approves or rejects; decision is immutable/audited
  → Doctor receives result
  → if approved, Doctor generates an allowlisted medical package
  → SMTP outbox sends to selected hospital transfer email
  → attempt, checksum and final provider status are recorded
```

Distance can be a deterministic tie-breaker only where valid coordinates exist. It is never invented or inferred from free text. No recommendation is labeled “AI.”

## H.7 Death certificate

```text
Authorized Doctor marks patient deceased through controlled workflow
  → drafts certificate
  → validates required jurisdiction-approved fields
  → issues immutable numbered certificate and generated PDF
  → authorized Guard receives notification
  → Guard views/prints issued copy
  → each view/print is logged
  → correction requires Doctor void + reissue with reason
```

## H.8 Messaging state

```text
Sender posts message with client id
  → membership and patient-context eligibility validated
  → Message + recipient receipts stored
  → sender sees Sent
  → recipient connection receives event and acknowledges delivery
  → receipt.delivered_at set; sender sees Delivered
  → recipient opens conversation and acknowledges seen cursor
  → receipt.seen_at set; sender sees Seen
```

## H.9 Calling state

```text
Caller selects an eligible participant
  → backend validates relationship and Twilio availability
  → CallSession persisted as Queued
  → short-lived provider token/instructions issued
  → signed provider callbacks move Ringing → In Progress → terminal state
  → both clients receive persisted state updates
  → call history records participants, timing and result, not call audio
```

## H.10 Billing

```text
Accounting selects patient/episode without clinical details
  → adds catalog/manual authorized charge lines
  → issues invoice snapshot
  → records payment with idempotent receipt number
  → totals/status update atomically
  → reversal uses explicit event, never deletion
  → financial report uses Accounting scope
```

---

# I. UI/UX design system

## I.1 Dribbble research synthesis

The visual direction is informed by multiple references rather than copied from one shot:

- FocoTik's medical clinic dashboard emphasizes centralized patient records, pending work, readable hierarchy, restrained blue/white styling, and charts connected to decisions rather than decoration [1](https://dribbble.com/shots/24899734-Medical-Dashboard-for-Effective-Patient-Management-ProvoHeal).
- Atheeb's hospital dashboards emphasize role-specific views, simple navigation, operational overview, and mobile adaptation [4](https://dribbble.com/shots/24457892-Hospital-Management-System-Dashboards).
- Hiren Panara's tablet-oriented doctor dashboard emphasizes minimizing clicks, trend visibility, patient history, and secure communication on an important hospital form factor [2](https://dribbble.com/shots/23846634-AI-Medical-iPad-Dashboard).
- Shakuro's check-in dashboard focuses on reducing confusion around records, treatment plans, next actions, and contacting care staff [7](https://dribbble.com/shots/23316432-Medical-Check-In-Web-Dashboard).

Extracted principles: clear role context, a compact action queue, patient identity always visible on clinical details, restrained semantic color, tablet usability, and progressive disclosure. Velora will not copy layouts, branding, illustrations, text, or assets from these references.

## I.2 Design direction

**Character:** calm, clinical, trustworthy, precise, human, and efficient.
**Primary form factor:** desktop and hospital tablet; mobile remains fully functional for Guard actions and time-sensitive staff tasks.
**Density:** comfortable by default with compact table mode available later; never oversized marketing-dashboard cards in work queues.

The interface uses a quiet neutral canvas and strong typographic hierarchy. Urgency is communicated locally around the affected patient/action, not by coloring an entire dashboard red.

## I.3 Color tokens

| Purpose | Proposed token | Usage |
|---|---:|---|
| App background | `#F5F7FA` | Low-contrast page canvas |
| Surface | `#FFFFFF` | Panels, forms, tables |
| Surface subtle | `#EDF2F6` | Selected/secondary areas |
| Text strong | `#17212B` | Main headings and values |
| Text muted | `#5F6F7E` | Labels and helper text |
| Border | `#D8E1E8` | Dividers and input borders |
| Primary | `#176B87` | Main actions, active navigation |
| Primary hover | `#12566D` | Interaction state |
| Information | `#2563A6` | Informational status |
| Success/stable | `#167A58` | Stable/completed with label/icon |
| Warning/due | `#A76512` | Due soon/attention |
| Critical | `#B93845` | Critical/overdue/destructive |
| Focus ring | `#2B89AD` | Keyboard focus indicator |

Final shades will be contrast-tested against WCAG 2.2 AA. Color is never the sole status signal: every state has text, icon/shape, and accessible name. Large red filled areas are reserved for true critical banners or destructive confirmations.

## I.4 Typography

- **Typeface:** self-hosted Inter Variable, with system sans-serif fallback. One family reduces visual noise and external network dependency.
- **Page title:** 28/36, weight 650.
- **Section heading:** 20/28, weight 650.
- **Card/table heading:** 16/24, weight 600.
- **Body:** 15/22, weight 400.
- **Labels/metadata:** 13/18, weight 500.
- **Critical values:** 16–20 with tabular numerals; units remain visible and are never encoded as placeholders.
- Line lengths are constrained on forms and notes. All dates include an unambiguous format; clinical times display the hospital timezone.

## I.5 Spacing, layout, and hierarchy

- 4px base spacing system: 4, 8, 12, 16, 20, 24, 32, 40, 48.
- 12-column responsive content grid with a practical maximum width around 1600px, not a narrow marketing layout.
- Desktop sidebar approximately 256px; collapsible to an icon rail. Tablet uses a compact rail/drawer. Mobile uses a drawer or role-appropriate bottom navigation for the highest-frequency sections.
- Page header contains title, patient/role context, one primary action, and secondary actions in a menu.
- Detail pages use stable tabs: Overview, Clinical Timeline, Vitals, Medication, Monitoring, Transfers, Documents, subject to role permissions.
- A persistent patient identity strip shows name, MRN, age/date of birth, care status, and critical precautions. It avoids confusing one patient's action with another.

## I.6 Component principles

- **Buttons:** one clear primary action per region; destructive actions separated and confirmed with the affected patient/object named.
- **Forms:** labels above inputs, required markers and explanations, units adjacent to measurement controls, inline field errors plus a summary that focuses the first error.
- **Status badges:** compact text + icon, neutral backgrounds, no ambiguous color dots alone.
- **Cards:** used for summaries, attention items, and grouped patient context—not as wrappers around every paragraph.
- **Tables:** used for staff, patients, resources, doses, transfers, and billing. They support sticky headers, meaningful default sort, filters, search, pagination, row focus, and action menus.
- **Timeline:** used for longitudinal medical events and status histories; event type, author, timestamp, and visibility are explicit.
- **Modal/dialog:** only for focused confirmation or short input. Patient registration, prescriptions, transfer composition, and records use dedicated pages.
- **Toasts:** confirm noncritical actions. Critical results remain in the page/notification center until acknowledged; they do not disappear as a toast.
- **Empty states:** explain why no data exists, whether filtering caused it, and the permitted next action.
- **Skeletons:** mirror stable page structure; spinners are reserved for small local actions.

## I.7 Role-specific dashboard composition

### Head of Service

1. Attention: expired staff invitations, unavailable resources, unstaffed departments, incomplete external-hospital contacts.
2. Operational summaries: active staff, occupied/available beds, service availability.
3. Next actions: invite staff, update resource, complete transfer directory.
4. Trends only when operationally useful; no clinical record content.

### Doctor

1. Critical patient alerts and unacknowledged changes.
2. Pending Guard transfer decisions and new monitoring responses.
3. Assigned patients requiring review.
4. Recent medication exceptions and transfer activity.
5. Primary actions: register patient, open critical patient, write prescription.

### Nurse

1. Due/overdue medication doses in time order.
2. Critical assigned patients and vitals requiring follow-up.
3. Patients without an active Guard link.
4. Primary actions: record vitals, confirm dose, invite Guard.

### Patient Guard

1. Decisions/questions requiring action.
2. Current patient selector when linked to multiple patients.
3. Active prescriptions and understandable schedule.
4. Transfer/certificate/message updates.
5. Medical terminology receives plain-language supporting labels without changing the official record.

### Accounting

1. Issued/overdue invoices, today's payments, reconciliation exceptions.
2. Quick patient billing lookup that excludes clinical detail.
3. Financial trend/chart only when it supports reconciliation or cash-flow review.

### Admin

1. Locked/deactivated accounts, failed login trend, integration availability, scheduler/outbox failures.
2. User and system configuration actions.
3. Audit information with protected clinical content redacted.

## I.8 Tables and data visualization

Tables have an explicit empty result after filters, removable filter chips, sortable labeled columns, and a visible result count. Row actions are keyboard accessible and dangerous actions are not hidden beside routine actions without separation.

Charts are limited to questions a user must answer:

- Vital trend for one metric over time, with units, exact points, and critical-rule annotations.
- Bed/resource availability trend for Head of Service.
- Medication administered/missed/refused trend where it changes action.
- Billing collection/aging for Accounting.

Every chart has a textual summary or accessible table, named axes, timezone, and no misleading truncated scale. Decorative donut charts for simple counts are avoided.

## I.9 Alerts and notification behavior

- **Critical:** persistent banner or queue row, critical icon, patient identity, timestamp, reason, and direct “Review patient” action.
- **Warning/due:** amber, ordered by deadline, with snooze only if policy permits.
- **Success:** quiet confirmation; does not compete with current clinical alerts.
- Alert acknowledgement is separate from resolution. Reading an alert does not mark a patient stable.
- Notification counts are server-derived and update across tabs/devices.

## I.10 Responsive and accessibility behavior

- Target WCAG 2.2 AA: keyboard navigation, visible focus, semantic headings, landmarks, correct labels, live regions for status changes, and no hover-only action.
- Minimum 44×44 touch target for primary tablet/mobile actions.
- At narrow widths, lower-priority table columns collapse into a labeled detail region; clinical labels and units never disappear.
- Forms use appropriate mobile input modes but do not sacrifice validation or confirmation.
- Guard workflows are optimized for mobile; staff workflows remain usable on tablet without requiring precise mouse interaction.
- Print styles produce a clear issued death certificate and billing receipt without navigation or hidden provenance.

## I.11 Animation

- 120–220ms transitions for navigation rail, dialog, status update, and notification insertion.
- Use opacity/transform rather than layout-heavy motion.
- No animation on critical values that could distract or imply monitoring hardware behavior.
- Honor `prefers-reduced-motion`; essential state changes remain understandable without motion.

---

# J. Implementation roadmap

Development proceeds as tested vertical slices. A phase is not complete when pages merely render; its database, policy, API, UI states, audit behavior, and tests must work together.

## Phase 0 — Architecture approval and clinical-policy inputs

- Review this document.
- Confirm open decisions below.
- Obtain hospital-approved vital rule definitions, medication missed-dose policy, transfer consent wording, death-certificate fields, and data-retention policy.
- Define acceptance scenarios for each role.

**Gate:** architecture and policy assumptions approved. No application code before this gate.

## Phase 1 — Engineering foundation

- Django/DRF project, settings split, SQLite configuration, migrations, request IDs, error envelope.
- React/Vite/TypeScript project, design tokens, application shell, API client, query/form foundation.
- Custom User, invitations, session/CSRF authentication, login/logout/reset, role and object-policy primitives.
- Audit primitives, secure file foundation, CI lint/test commands.
- Role shells and navigation only; no empty feature-page explosion.

**Why first:** every later workflow depends on trustworthy identity, access policy, errors, and a stable transaction/audit foundation.

## Phase 2 — Head of Service configuration

- Hospital profile, departments, staff, specialties/conditions, services.
- Rooms, beds, resources.
- External hospitals and capability directory.
- Versioned vital metric/rule configuration without seeded medical thresholds.

**Gate:** Head of Service can prepare all reference data required for intake, rules, and transfer.

## Phase 3 — First end-to-end vertical slice: patient intake

- Doctor patient registration + medical file + care episode + Nurse assignment.
- Nurse assigned-patient dashboard.
- Guard invitation/acceptance/access link.
- Scoped patient lists/details and permission tests for guessed IDs.

**Why this slice first:** it establishes the core relationship graph that every clinical feature uses and proves cross-role notifications and RBAC early.

## Phase 4 — Clinical file and vital-alert loop

- Timeline, allergy/history/diagnosis/treatment/note foundations.
- Nurse vital entry.
- Versioned evaluation service and explanation.
- Critical Doctor alert, acknowledgement, trends, and audit access.
- Edge cases: no rule set, incomplete metrics, changed rule version, duplicate submit.

## Phase 5 — Prescription and medication loop

- Medication vocabulary, prescription drafting/activation/revision.
- Structured schedule generation.
- Guard prescription view.
- Nurse due queue and administer/refuse/miss transitions.
- Scheduler worker, deduped alerts, exception notification, concurrency tests.

## Phase 6 — Monitoring conversation

- Doctor threads/questions, Guard responses, history/supersession, notifications.
- Typed answer validation and role/object-scope tests.

## Phase 7 — Transfer and death-certificate workflows

- Transfer requirement capture, deterministic recommendation, explainability snapshot.
- Guard decision, transition state machine, SMTP outbox/package, retry/audit.
- Death certificate draft/issue/void/reissue and guarded view/print.

## Phase 8 — Communication

- Conversation eligibility, messages, attachments, receipts, cursors.
- WebSocket event delivery and REST reconnection synchronization.
- Twilio adapter, token endpoint, signed webhooks, call states, and unavailable-integration UX.

## Phase 9 — Accounting, reporting, and administration

- Charge catalogue, invoices, payments, reversals, receipts.
- Strict clinical-data exclusion.
- Role-scoped operational/clinical/financial reports.
- Admin users, system health, outbox/integration monitoring, redacted audit views.

## Phase 10 — Security and resilience hardening

- Threat-model review, ID-guessing and horizontal-access tests, CSRF/CORS/origin tests.
- Rate limiting, invitation abuse controls, file validation, webhook signature/idempotency tests.
- SQLite contention tests, backup/restore drill, scheduler restart/retry tests.
- Dependency and secret scanning.

## Phase 11 — UI/UX refinement and accessibility

- Role usability walkthroughs and task-time checks.
- Responsive/tablet/mobile refinement.
- WCAG audit, reduced motion, print verification.
- Loading, partial failure, offline/retry, empty, conflict, and forbidden state review.
- Charts added only where validated as decision-supporting.

## Phase 12 — Release readiness

- Seed/reference-data command containing no real patient data.
- Deployment and environment guide, administrator runbook, backup/restore guide.
- User training material by role.
- Workflow acceptance tests and release sign-off.

## Test strategy throughout

- **Unit:** rule operators, recommendation scores, schedule generation, policy predicates, transition tables.
- **Model/constraint:** uniqueness, date ranges, state checks, protected deletes.
- **API:** validation, status codes, idempotency, pagination, file authorization.
- **Permission matrix:** every role/action plus cross-patient UUID guessing.
- **Workflow integration:** intake → Guard; vitals → Doctor; prescription → dose; transfer → approval → SMTP; message → delivered → seen.
- **Frontend component:** forms, errors, keyboard/focus, responsive states.
- **End-to-end:** realistic role handoffs using database seed factories, never hardcoded production UI data.

---

# K. Decisions requested before implementation

The following recommendations need approval or correction:

1. **Browser authentication:** approve secure Django session cookies + CSRF instead of browser-stored JWTs.
2. **Rule governance:** Head of Service can version and approve vital rules. No thresholds are shipped until hospital-approved values are supplied.
3. **Patient registration:** registering Doctor becomes the primary Doctor and must select an active primary Nurse in the same transaction.
4. **Guard visibility:** Patient Guard sees only explicitly released medical-file fields plus active prescriptions, their monitoring, transfer decisions, and issued certificates.
5. **Transfer order:** Doctor records requirements, generates recommendations, selects destination, then submits to the designated Guard; SMTP transmission is allowed only after approval.
6. **Messaging transport:** durable REST + same-application WebSocket events, with REST recovery after disconnect.
7. **Scheduler:** an idempotent Django management worker handles due-dose alerts/outbox retries without Celery or another datastore.
8. **Admin boundaries:** Admin manages system identity/configuration but has no default clinical-record access; no break-glass flow in the first release.
9. **Twilio behavior:** calling is enabled only when credentials/webhooks are configured; otherwise the UI explains that calling is unavailable and never simulates success.
10. **Certificate policy:** jurisdiction-specific mandatory fields, numbering, signatory requirements, and legal print wording must be provided before the death-certificate phase.
11. **Billing visibility:** Accounting has demographic/billing-only access. Guard billing access remains off unless explicitly granted and approved.
12. **Deployment scale:** initial deployment uses SQLite-compatible single-primary application topology; horizontal database scale is outside scope.

Approval of this document, with any amendments to these decisions, is the entry condition for Phase 1.
