import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, CheckCircle2, Pill, Plus, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { getPatient } from '../../patient-care/shared/api'
import { activatePrescription, cancelPrescription, completePrescription, getPrescriptions } from '../../prescriptions/shared/api'
import type { Prescription } from '../../prescriptions/shared/types'

export function DoctorPrescriptionsPage() {
  const { patientId } = useParams()
  const client = useQueryClient()
  const [cancelling, setCancelling] = useState<Prescription | null>(null)
  const [reason, setReason] = useState('')
  const query = useQuery({ queryKey: ['prescriptions', patientId ?? 'all'], queryFn: () => getPrescriptions(patientId) })
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId!), enabled: Boolean(patientId) })
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ['prescriptions'] }), client.invalidateQueries({ queryKey: ['notifications'] })])
  const activate = useMutation({ mutationFn: activatePrescription, onSuccess: refresh })
  const complete = useMutation({ mutationFn: completePrescription, onSuccess: refresh })
  const cancel = useMutation({ mutationFn: () => cancelPrescription(cancelling!.id, reason), onSuccess: async () => { setCancelling(null); setReason(''); await refresh() } })
  const error = activate.error ?? complete.error
  const createTarget = patientId ? `/doctor/prescriptions/new?patient=${patientId}` : '/doctor/prescriptions/new'
  return <div className="workspace-page"><PageHeader eyebrow="Medication orders" title={patient.data ? `${patient.data.full_name} · Prescriptions` : 'Prescriptions'} description="Create drafts, verify schedules, activate medication orders and monitor dose outcomes." actions={<Link className="button button--primary" to={createTarget}><Plus size={16} /> New prescription</Link>} />{error && <Alert tone="critical">{error instanceof AppApiError ? error.message : 'Prescription transition failed.'}</Alert>}{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Prescriptions could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No prescriptions" description="Create a complete draft for an assigned patient, then activate its medication schedule." action={<Link className="button button--primary" to={createTarget}>Create prescription</Link>} /></section> : <div className="prescription-list">{query.data!.map((prescription) => <article key={prescription.id} className="prescription-card"><header><div><span className="prescription-card__icon"><Pill /></span><div><h2>{prescription.patient_name}</h2><p>{prescription.medical_record_number} · Prescribed by {prescription.prescribed_by_name}</p></div></div><StatusBadge status={prescription.status} /></header><div className="prescription-card__meta"><span><CalendarDays /> {prescription.starts_on} to {prescription.ends_on}</span><span>{prescription.items.length} medication {prescription.items.length === 1 ? 'item' : 'items'}</span></div><div className="prescription-medications">{prescription.items.map((item) => <section key={item.id}><div><strong>{item.medication_name}</strong><span>{Number(item.dose_amount)} {item.dose_unit} · {item.route.toLowerCase()}</span></div><p>{item.frequency_display} for {item.duration_days} days{item.instructions ? ` · ${item.instructions}` : ''}</p><div className="schedule-chips">{item.schedule_rules.map((rule) => <span key={rule.id}>{rule.local_time.slice(0, 5)} · {rule.days_of_week.length ? rule.days_of_week.map((day) => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day]).join(', ') : 'Daily'}</span>)}</div></section>)}</div>{prescription.clinical_instructions && <p className="prescription-instructions"><strong>Clinical instructions:</strong> {prescription.clinical_instructions}</p>}<div className="dose-summary"><span>Pending <strong>{prescription.dose_summary.PENDING}</strong></span><span>Administered <strong>{prescription.dose_summary.ADMINISTERED}</strong></span><span>Missed <strong>{prescription.dose_summary.MISSED}</strong></span><span>Refused <strong>{prescription.dose_summary.REFUSED}</strong></span></div><footer>{prescription.status === 'DRAFT' && <Button onClick={() => activate.mutate(prescription.id)} isLoading={activate.isPending}><CheckCircle2 size={16} /> Activate schedule</Button>}{prescription.status === 'ACTIVE' && <Button variant="secondary" onClick={() => complete.mutate(prescription.id)} isLoading={complete.isPending}>Complete prescription</Button>}{['DRAFT', 'ACTIVE'].includes(prescription.status) && <Button variant="ghost" onClick={() => { setCancelling(prescription); setReason('') }}><XCircle size={16} /> Cancel</Button>}</footer></article>)}</div>}<Modal open={Boolean(cancelling)} onClose={() => setCancelling(null)} title="Cancel prescription" description="All pending scheduled doses will be cancelled. Recorded administrations remain in history."><form onSubmit={(event) => { event.preventDefault(); cancel.mutate() }}><TextAreaField label="Cancellation reason" required rows={4} value={reason} onChange={(event) => setReason(event.target.value)} />{cancel.error && <Alert tone="critical">{cancel.error instanceof AppApiError ? cancel.error.message : 'Cancellation failed.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setCancelling(null)}>Keep prescription</Button><Button type="submit" variant="danger" isLoading={cancel.isPending}>Cancel prescription</Button></div></form></Modal></div>
}
