# Hospital Acceptance Test Plan

Use a dedicated staging database containing no production patient information. Record tester, role, timestamp, build commit, result, and evidence for every scenario.

## 1. Identity and access

- Admin creates or invites approved privileged roles.
- Head of Service invites Doctor and Nurse but cannot create Admin.
- Nurse invitation creates Patient Guard only in an assigned-patient context.
- Expired, revoked, and reused invitation tokens fail.
- Temporary-password account can access password change only.
- Every role is denied a guessed patient UUID without the required relationship.
- Admin, Head of Service, and Accounting cannot open clinical records by default.

## 2. Hospital preparation

- Configure hospital identity, departments, services, rooms, beds, resources, medications, specialties, conditions, and external hospitals.
- Deactivate each reference item and confirm historical records remain intact.
- Create a draft vital rule set, validate operators, activate it, then activate a replacement and confirm the first is retired.
- Confirm no threshold exists unless entered by clinical governance.

## 3. Patient intake

- Doctor registers a patient and assigns an active Nurse.
- Confirm Patient, MedicalFile, CareEpisode, Doctor assignment, Nurse assignment, audit event, and Nurse notification are created together.
- Submit the same current patient identity and confirm duplicate handling creates no partial rows.
- Reassign Nurse and confirm the previous Nurse immediately loses patient access.

## 4. Patient Guard

- Assigned Nurse sends invitation with selected permissions.
- Guard accepts and sees exactly the linked patient.
- Disable medical-file, monitoring, transfer, and billing permissions independently and verify each boundary.
- Revoke Guard access and verify all patient-scoped endpoints become unavailable.

## 5. Clinical records and vitals

- Doctor records diagnosis/treatment; Nurse cannot diagnose.
- Nurse writes a Nursing note but cannot write a Doctor-only note type.
- Sign a note and confirm it cannot be edited.
- Release one record to Guard; confirm internal records remain hidden.
- Record vitals with no active rules and confirm Unassessed.
- Use hospital-approved synthetic staging rules to confirm Stable and Critical paths.
- Confirm the Critical explanation and Doctor notification identify the stored rule snapshot.

## 6. Prescription and medication

- Doctor creates multi-item draft with explicit times and weekdays.
- Guard cannot see draft.
- Activate and verify concrete dose rows and Guard visibility.
- Due worker creates one notification per Nurse/dose despite repeated runs.
- Nurse records Administered, Missed, and Refused outcomes.
- Duplicate administration fails and the append-only event count remains correct.
- Cancel an active prescription and confirm pending doses become Cancelled while completed events remain.

## 7. Monitoring and transfer

- Doctor asks Boolean, text, numeric, and choice questions.
- Guard answers and corrects one response; verify superseded history.
- Generate transfer recommendations from mandatory/optional specialty, service, and condition requirements.
- Verify score, matched/missing reasons, source generation, and deterministic ordering.
- Attempt ineligible destination selection and confirm rejection.
- Guard rejects one request with reason and approves another.
- Verify package sending is impossible before approval.
- Send through staging SMTP and verify recipient, checksum, allowlisted contents, status, and audit record.

## 8. Death certificate

- Doctor creates draft; Guard cannot see it.
- Issue and confirm patient status and Guard notification.
- Guard opens printable view and print access is logged.
- Guard cannot create, edit, issue, or void.
- Void with reason and confirm prior record remains in history.
- Confirm jurisdiction-approved wording and numbering with legal owner.

## 9. Communication

- Create only conversations shown by eligible-contact rules.
- Exchange messages in both directions and observe Sent → Delivered → Seen.
- Retry a client message ID and confirm no duplicate.
- Upload every allowed file type and reject disguised/oversized/disallowed files.
- Nonparticipant download returns not found.
- Disconnect/reconnect WebSocket and verify REST synchronization.
- With Twilio absent, confirm no simulated call.
- In Twilio staging, test incoming/outgoing call, signature rejection, no-answer, declined, failed, and completed states.

## 10. Accounting and administration

- Accounting lookup contains identity/billing fields only.
- Configure the hospital ISO 4217 billing currency and confirm each invoice preserves its currency snapshot after later profile changes.
- Create draft, lines, issue, partial payment, final payment, reversal, and void paths.
- Reject overpayment and void with posted payment.
- Grant/revoke Guard billing permission.
- Export CSV and reconcile totals.
- Admin suspends another user but cannot suspend self.
- Admin audit output contains no before/after clinical snapshots.
- Head operational report and Accounting financial report reject other roles.

## 11. Resilience and release

- Run all CI-equivalent commands.
- Create online backup, verify checksums and SQLite integrity.
- Restore into isolated staging and repeat role login plus one patient workflow.
- Kill/restart medication worker; confirm heartbeat and idempotent catch-up.
- Review tablet/mobile layouts, keyboard focus, modal focus trap, reduced motion, and certificate print.
- Complete `RELEASE_CHECKLIST.md` and obtain clinical, security, operations, and legal sign-off.
