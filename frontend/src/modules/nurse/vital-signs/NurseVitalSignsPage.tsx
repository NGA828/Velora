import { useQuery } from '@tanstack/react-query'
import { Activity, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { patientScore } from '../../vital-signs/shared/stability'
import { VitalStabilityMeter } from '../../vital-signs/shared/VitalStabilityMeter'

export function NurseVitalSignsPage() {
  const query = useQuery({ queryKey: ['patients', 'nurse'], queryFn: () => getPatients() })
  const patients = query.data ?? []
  const scored = patients.filter((patient) => patient.latest_vital_status)
  const criticalCount = scored.filter((patient) => patient.latest_vital_status === 'CRITICAL').length
  const stableCount = scored.filter((patient) => patient.latest_vital_status === 'STABLE').length

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Patient monitoring"
        title="Vital signs"
        description="Record temperature, pulse, respiration, blood pressure, and body weight. The system scores each observation as a stability or criticality percentage."
      />
      {query.isPending ? (
        <SectionLoader />
      ) : query.error ? (
        <Alert tone="critical">Assigned patients could not be loaded.</Alert>
      ) : (
        <>
          <section className="metric-grid metric-grid--three">
            <article className="metric-card">
              <span className="metric-card__icon metric-card__icon--teal">
                <Activity />
              </span>
              <div>
                <small>Monitored now</small>
                <strong>{patients.length}</strong>
                <p>Assigned patients</p>
              </div>
            </article>
            <article className="metric-card">
              <span className="metric-card__icon metric-card__icon--green">
                <Activity />
              </span>
              <div>
                <small>Latest stable</small>
                <strong>{stableCount}</strong>
                <p>No critical rule matched</p>
              </div>
            </article>
            <article className="metric-card">
              <span className="metric-card__icon metric-card__icon--red">
                <Activity />
              </span>
              <div>
                <small>Latest critical</small>
                <strong>{criticalCount}</strong>
                <p>Doctor notification generated</p>
              </div>
            </article>
          </section>
          <section className="section-panel">
            <div className="section-panel__heading">
              <div>
                <p className="eyebrow">Assigned patients</p>
                <h2>Monitoring status</h2>
              </div>
              <Activity />
            </div>
            {patients.length === 0 ? (
              <EmptyState
                title="No assigned patients"
                description="Patients appear here after a Doctor assigns you as the active Nurse."
              />
            ) : (
              <div className="vital-monitor-grid">
                {patients.map((patient) => {
                  const score = patientScore(patient)
                  return (
                    <article key={patient.id} className="vital-monitor-card">
                      <header>
                        <div>
                          <h3>{patient.full_name}</h3>
                          <p>
                            {patient.medical_record_number} · {patient.age} years
                          </p>
                        </div>
                      </header>
                      {score ? (
                        <VitalStabilityMeter score={score} />
                      ) : (
                        <p className="muted-copy">No vital signs recorded yet.</p>
                      )}
                      {patient.latest_vital_at && (
                        <small>Last recorded {new Date(patient.latest_vital_at).toLocaleString()}</small>
                      )}
                      <footer>
                        <Link className="button button--secondary" to={`/nurse/patients/${patient.id}/vitals`}>
                          History
                        </Link>
                        <Link className="button button--primary" to={`/nurse/patients/${patient.id}/vitals/new`}>
                          <Plus size={16} /> Record vitals
                        </Link>
                      </footer>
                    </article>
                  )
                })}
              </div>
            )}
            <div className="table-footer-note">
              Open a patient to record temperature, pulse, respiration, blood pressure, and body weight. Analysis uses only the hospital’s approved rule set.
            </div>
          </section>
        </>
      )}
    </div>
  )
}
