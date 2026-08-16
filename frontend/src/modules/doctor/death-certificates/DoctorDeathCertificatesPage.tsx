import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FilePlus2, ScrollText, XCircle } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { FormField } from '../../../shared/ui/forms/FormField'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { createDeathCertificate, getDeathCertificates, issueDeathCertificate, voidDeathCertificate } from '../../death-certificates/shared/api'
import type { DeathCertificate } from '../../death-certificates/shared/types'
import { getPatients } from '../../patient-care/shared/api'

export function DoctorDeathCertificatesPage() {
  const client = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [voiding, setVoiding] = useState<DeathCertificate | null>(null)
  const [voidReason, setVoidReason] = useState('')
  const [form, setForm] = useState({ patient: '', death_datetime: '', place_of_death: '', primary_cause: '', contributing_causes: '', manner_of_death: '', notes: '' })
  const query = useQuery({ queryKey: ['death-certificates', 'doctor'], queryFn: () => getDeathCertificates() })
  const patients = useQuery({ queryKey: ['patients', 'doctor'], queryFn: () => getPatients() })
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ['death-certificates'] }), client.invalidateQueries({ queryKey: ['patients'] }), client.invalidateQueries({ queryKey: ['notifications'] })])
  const createMutation = useMutation({ mutationFn: () => createDeathCertificate({ ...form, death_datetime: new Date(form.death_datetime).toISOString() }), onSuccess: async () => { setCreateOpen(false); await refresh() } })
  const issue = useMutation({ mutationFn: issueDeathCertificate, onSuccess: refresh })
  const voidMutation = useMutation({ mutationFn: () => voidDeathCertificate(voiding!.id, voidReason), onSuccess: async () => { setVoiding(null); await refresh() } })
  const transitionError = issue.error
  return <div className="workspace-page"><PageHeader eyebrow="Official medical record" title="Death certificates" description="Draft, issue and, when necessary, void certificates. Issued records are immutable to Patient Guards." actions={<Button onClick={() => { setCreateOpen(true); setForm({ patient: '', death_datetime: '', place_of_death: '', primary_cause: '', contributing_causes: '', manner_of_death: '', notes: '' }) }}><FilePlus2 size={16} /> Create certificate</Button>} />{transitionError && <Alert tone="critical">{transitionError instanceof AppApiError ? transitionError.message : 'Certificate transition failed.'}</Alert>}{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Certificates could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No death certificates" description="Only an assigned Doctor can create a certificate when required." /></section> : <div className="certificate-list">{query.data!.map((certificate) => <article key={certificate.id} className="certificate-card"><header><span><ScrollText /></span><div><h2>{certificate.patient_name}</h2><p>{certificate.certificate_number} · {certificate.medical_record_number}</p></div><StatusBadge status={certificate.status} /></header><dl><div><dt>Date and time of death</dt><dd>{new Date(certificate.death_datetime).toLocaleString()}</dd></div><div><dt>Place</dt><dd>{certificate.place_of_death}</dd></div><div><dt>Primary cause</dt><dd>{certificate.primary_cause}</dd></div><div><dt>Issuing Doctor</dt><dd>{certificate.issuing_doctor_name}</dd></div></dl><footer>{certificate.status === 'DRAFT' && <Button onClick={() => issue.mutate(certificate.id)}>Issue certificate</Button>}{certificate.status === 'ISSUED' && <Button variant="danger" onClick={() => { setVoiding(certificate); setVoidReason('') }}><XCircle size={16} /> Void certificate</Button>}</footer></article>)}</div>}
    <Modal open={createOpen} width="wide" onClose={() => setCreateOpen(false)} title="Create death certificate draft" description="Confirm jurisdiction-specific wording and hospital policy before issuing."><form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }}><SelectField label="Patient" required value={form.patient} onChange={(e) => setForm({ ...form, patient: e.target.value })}><option value="">Select assigned patient</option>{patients.data?.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name} · {patient.medical_record_number}</option>)}</SelectField><div className="form-grid"><FormField label="Date and time of death" type="datetime-local" required value={form.death_datetime} onChange={(e) => setForm({ ...form, death_datetime: e.target.value })} /><FormField label="Place of death" required value={form.place_of_death} onChange={(e) => setForm({ ...form, place_of_death: e.target.value })} /></div><TextAreaField label="Primary cause" required rows={3} value={form.primary_cause} onChange={(e) => setForm({ ...form, primary_cause: e.target.value })} /><TextAreaField label="Contributing causes" rows={2} value={form.contributing_causes} onChange={(e) => setForm({ ...form, contributing_causes: e.target.value })} /><FormField label="Manner of death" value={form.manner_of_death} onChange={(e) => setForm({ ...form, manner_of_death: e.target.value })} /><TextAreaField label="Doctor notes" rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />{createMutation.error && <Alert tone="critical">{createMutation.error instanceof AppApiError ? createMutation.error.message : 'Certificate could not be created.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button><Button type="submit" isLoading={createMutation.isPending}>Save draft</Button></div></form></Modal>
    <Modal open={Boolean(voiding)} onClose={() => setVoiding(null)} title="Void issued certificate" description="The original remains in audit history and becomes unavailable to Patient Guards."><form onSubmit={(event) => { event.preventDefault(); voidMutation.mutate() }}><TextAreaField label="Void reason" required rows={4} value={voidReason} onChange={(e) => setVoidReason(e.target.value)} />{voidMutation.error && <Alert tone="critical">{voidMutation.error instanceof AppApiError ? voidMutation.error.message : 'Certificate could not be voided.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setVoiding(null)}>Cancel</Button><Button type="submit" variant="danger" isLoading={voidMutation.isPending}>Void certificate</Button></div></form></Modal>
  </div>
}
