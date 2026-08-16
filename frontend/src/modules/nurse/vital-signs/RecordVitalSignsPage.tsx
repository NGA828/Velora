import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, ArrowLeft, Save, ShieldAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { FormField } from '../../../shared/ui/forms/FormField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { createVitalObservation, getVitalMetrics } from '../../vital-signs/shared/api'

function localDateTimeValue() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

export function RecordVitalSignsPage() {
  const { patientId = '' } = useParams()
  const client = useQueryClient()
  const [observedAt, setObservedAt] = useState(localDateTimeValue)
  const [notes, setNotes] = useState('')
  const [measurements, setMeasurements] = useState<Record<string, string>>({})
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  const metrics = useQuery({ queryKey: ['vital-metrics'], queryFn: getVitalMetrics })
  const activeMetrics = useMemo(() => metrics.data?.filter((metric) => metric.is_active) ?? [], [metrics.data])
  const mutation = useMutation({
    mutationFn: () => createVitalObservation({ patient: patientId, observed_at: new Date(observedAt).toISOString(), notes, values: activeMetrics.filter((metric) => measurements[metric.id]?.trim()).map((metric) => ({ metric: metric.id, value: measurements[metric.id] })) }),
    onSuccess: async () => { await Promise.all([client.invalidateQueries({ queryKey: ['vital-observations', patientId] }), client.invalidateQueries({ queryKey: ['patient', patientId] }), client.invalidateQueries({ queryKey: ['patients'] }), client.invalidateQueries({ queryKey: ['patient-dashboard'] }), client.invalidateQueries({ queryKey: ['notifications'] })]) },
  })
  const hasValue = Object.values(measurements).some((value) => value.trim())

  return <div className="workspace-page workspace-page--narrow"><div className="back-link"><Link to={`/nurse/patients/${patientId}`}><ArrowLeft size={16} /> Back to patient overview</Link></div><PageHeader eyebrow="Patient monitoring" title={patient.data ? `Record vitals · ${patient.data.full_name}` : 'Record vital signs'} description="Measurements are evaluated only against the hospital’s active approved rule set." /><PatientPageState pending={patient.isPending || metrics.isPending} error={patient.error ?? metrics.error} />{patient.data && activeMetrics.length === 0 && <section className="section-panel"><EmptyState title="No active vital metrics" description="The Head of Service must configure metric definitions before Nurses can record measurements." /></section>}{patient.data && activeMetrics.length > 0 && <form className="vital-entry-form" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}><section className="section-panel"><div className="form-section-heading"><span><Activity size={16} /></span><div><h2>Observed measurements</h2><p>Enter only measurements actually taken. Units are fixed by hospital configuration.</p></div></div><FormField label="Observation time" type="datetime-local" required value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /><div className="vital-input-grid">{activeMetrics.map((metric) => <FormField key={metric.id} label={`${metric.name} (${metric.unit})`} type="number" step={metric.decimal_places === 0 ? '1' : `0.${'0'.repeat(Math.max(0, metric.decimal_places - 1))}1`} helperText={metric.description || `Metric code: ${metric.code}`} value={measurements[metric.id] ?? ''} onChange={(event) => setMeasurements({ ...measurements, [metric.id]: event.target.value })} />)}</div><TextAreaField label="Nurse notes (optional)" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></section><Alert tone="information" title="No hidden thresholds"><ShieldAlert size={16} /> The result can be Stable, Critical, or Unassessed. Unassessed is used when approved rule coverage is incomplete.</Alert>{mutation.error && <Alert tone="critical" title="Vital signs were not saved">{mutation.error instanceof AppApiError ? mutation.error.message : 'Review the measurements and try again.'}</Alert>}{mutation.data && <Alert tone={mutation.data.status === 'CRITICAL' ? 'critical' : mutation.data.status === 'STABLE' ? 'success' : 'information'} title="Observation saved"><span className="inline-status-result"><StatusBadge status={mutation.data.status} /> {mutation.data.status === 'CRITICAL' ? 'The assigned Doctor has been notified.' : mutation.data.status === 'STABLE' ? 'No configured critical rule matched.' : 'The measurements could not be fully assessed.'}</span><Link to={`/nurse/patients/${patientId}/vitals`}>View vital history</Link></Alert>}<div className="registration-submit"><div><ShieldAlert /><span><strong>Explainable evaluation</strong><small>Every matched rule is stored with its values.</small></span></div><Button type="submit" disabled={!hasValue} isLoading={mutation.isPending}><Save size={17} /> Save and analyze</Button></div></form>}</div>
}
