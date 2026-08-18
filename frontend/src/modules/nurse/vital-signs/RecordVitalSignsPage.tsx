import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, ArrowLeft, Save, Scale, ShieldAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { FormField } from '../../../shared/ui/forms/FormField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { createVitalObservation, getVitalMetrics } from '../../vital-signs/shared/api'
import type { VitalMetric } from '../../vital-signs/shared/types'
import { VitalStabilityMeter } from '../../vital-signs/shared/VitalStabilityMeter'

function localDateTimeValue() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

function metricStep(metric: VitalMetric) {
  return metric.decimal_places === 0 ? '1' : `0.${'0'.repeat(Math.max(0, metric.decimal_places - 1))}1`
}

function MetricFields({
  metrics,
  measurements,
  onChange,
}: {
  metrics: VitalMetric[]
  measurements: Record<string, string>
  onChange: (metricId: string, value: string) => void
}) {
  return (
    <div className="vital-input-grid">
      {metrics.map((metric) => (
        <FormField
          key={metric.id}
          label={`${metric.name} (${metric.unit})`}
          type="number"
          step={metricStep(metric)}
          helperText={metric.description || `Metric code: ${metric.code}`}
          value={measurements[metric.id] ?? ''}
          onChange={(event) => onChange(metric.id, event.target.value)}
        />
      ))}
    </div>
  )
}

export function RecordVitalSignsPage() {
  const { patientId = '' } = useParams()
  const client = useQueryClient()
  const [observedAt, setObservedAt] = useState(localDateTimeValue)
  const [notes, setNotes] = useState('')
  const [measurements, setMeasurements] = useState<Record<string, string>>({})
  const patient = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
    enabled: Boolean(patientId),
  })
  const metrics = useQuery({ queryKey: ['vital-metrics'], queryFn: getVitalMetrics })
  const activeMetrics = useMemo(
    () => [...(metrics.data ?? [])].filter((metric) => metric.is_active).sort((left, right) => (left.display_order ?? 100) - (right.display_order ?? 100) || left.name.localeCompare(right.name)),
    [metrics.data],
  )
  const primaryMetrics = activeMetrics.filter((metric) => metric.contributes_to_assessment)
  const additionalMetrics = activeMetrics.filter((metric) => !metric.contributes_to_assessment)
  const bloodPressure = primaryMetrics.filter((metric) => metric.code === 'SBP' || metric.code === 'DBP')
  const otherPrimary = primaryMetrics.filter((metric) => metric.code !== 'SBP' && metric.code !== 'DBP')
  const mutation = useMutation({
    mutationFn: () =>
      createVitalObservation({
        patient: patientId,
        observed_at: new Date(observedAt).toISOString(),
        notes,
        values: activeMetrics
          .filter((metric) => measurements[metric.id]?.trim())
          .map((metric) => ({ metric: metric.id, value: measurements[metric.id] })),
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['vital-observations', patientId] }),
        client.invalidateQueries({ queryKey: ['patient', patientId] }),
        client.invalidateQueries({ queryKey: ['patients'] }),
        client.invalidateQueries({ queryKey: ['patient-dashboard'] }),
        client.invalidateQueries({ queryKey: ['notifications'] }),
      ])
    },
  })
  const hasValue = Object.values(measurements).some((value) => value.trim())
  const updateMeasurement = (metricId: string, value: string) => {
    setMeasurements((current) => ({ ...current, [metricId]: value }))
  }

  return (
    <div className="workspace-page workspace-page--narrow">
      <div className="back-link">
        <Link to={`/nurse/patients/${patientId}`}>
          <ArrowLeft size={16} /> Back to patient overview
        </Link>
      </div>
      <PageHeader
        eyebrow="Patient monitoring"
        title={patient.data ? `Record vitals · ${patient.data.full_name}` : 'Record vital signs'}
        description="Temperature, pulse, respiration, blood pressure, and body weight are analyzed against the hospital’s active approved rule set. The result is shown as a stability or criticality percentage."
      />
      <PatientPageState pending={patient.isPending || metrics.isPending} error={patient.error ?? metrics.error} />
      {patient.data && activeMetrics.length === 0 && (
        <section className="section-panel">
          <EmptyState
            title="No active vital metrics"
            description="The Head of Service must configure metric definitions before Nurses can record measurements."
          />
        </section>
      )}
      {patient.data && activeMetrics.length > 0 && (
        <form
          className="vital-entry-form"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
        >
          <section className="section-panel">
            <div className="form-section-heading">
              <span>
                <Activity size={16} />
              </span>
              <div>
                <h2>Primary vital signs</h2>
                <p>Enter only measurements actually taken. Units are fixed by hospital configuration.</p>
              </div>
            </div>
            <FormField label="Observation time" type="datetime-local" required value={observedAt} onChange={(event) => setObservedAt(event.target.value)} />
            <MetricFields metrics={otherPrimary} measurements={measurements} onChange={updateMeasurement} />
            {bloodPressure.length > 0 && (
              <div className="vital-subgroup">
                <h3>Blood pressure</h3>
                <p>Record systolic over diastolic as two measurements.</p>
                <MetricFields metrics={bloodPressure} measurements={measurements} onChange={updateMeasurement} />
              </div>
            )}
          </section>
          {additionalMetrics.length > 0 && (
            <section className="section-panel">
              <div className="form-section-heading">
                <span>
                  <Scale size={16} />
                </span>
                <div>
                  <h2>Additional measurements</h2>
                  <p>Body weight is stored with the observation. It is scored only if a hospital rule is configured for it.</p>
                </div>
              </div>
              <MetricFields metrics={additionalMetrics} measurements={measurements} onChange={updateMeasurement} />
            </section>
          )}
          <section className="section-panel">
            <TextAreaField label="Nurse notes (optional)" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
          </section>
          <Alert tone="information" title="Explainable percentage">
            <ShieldAlert size={16} /> Each scored vital is compared with the active rule set. Stable is the share of assessed vitals that did not match a critical rule. Critical is the share that did. Unassessed is used when approved rule coverage is incomplete.
          </Alert>
          {mutation.error && (
            <Alert tone="critical" title="Vital signs were not saved">
              {mutation.error instanceof AppApiError ? mutation.error.message : 'Review the measurements and try again.'}
            </Alert>
          )}
          {mutation.data && (
            <section className={`vital-result vital-result--${mutation.data.status.toLowerCase()}`}>
              <VitalStabilityMeter score={mutation.data} size="lg" />
              <p>
                {mutation.data.status === 'CRITICAL'
                  ? 'The assigned Doctor has been notified.'
                  : mutation.data.status === 'STABLE'
                    ? 'No configured critical rule matched.'
                    : 'The measurements could not be fully assessed.'}
              </p>
              <Link to={`/nurse/patients/${patientId}/vitals`}>View vital history</Link>
            </section>
          )}
          <div className="registration-submit">
            <div>
              <ShieldAlert />
              <span>
                <strong>Save and analyze</strong>
                <small>Every matched rule is stored with its values.</small>
              </span>
            </div>
            <Button type="submit" disabled={!hasValue} isLoading={mutation.isPending}>
              <Save size={17} /> Save and analyze
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
