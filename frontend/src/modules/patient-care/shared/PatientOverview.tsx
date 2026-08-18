import { CalendarDays, FileText, HeartHandshake, MapPin, Phone, ShieldCheck, UsersRound } from 'lucide-react'

import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { patientScore } from '../../vital-signs/shared/stability'
import { VitalStabilityMeter } from '../../vital-signs/shared/VitalStabilityMeter'
import type { PatientDetail } from './types'

export function PatientOverview({ patient }: { patient: PatientDetail }) {
  const score = patientScore(patient)
  return (
    <div className="patient-overview">
      <section className="patient-identity-card">
        <div className="patient-identity-card__main">
          <span className="patient-avatar">
            {patient.first_name[0]}
            {patient.last_name[0]}
          </span>
          <div>
            <div className="patient-identity-card__title">
              <h2>{patient.full_name}</h2>
              <StatusBadge status={patient.status} />
            </div>
            <p>
              {patient.medical_record_number} · {patient.age} years · {patient.sex_at_birth.toLowerCase().replaceAll('_', ' ')}
            </p>
          </div>
          {score && <VitalStabilityMeter score={score} size="sm" showDetail={false} />}
        </div>
        <dl>
          <div>
            <dt>
              <CalendarDays /> Date of birth
            </dt>
            <dd>{new Date(`${patient.date_of_birth}T00:00:00`).toLocaleDateString()}</dd>
          </div>
          <div>
            <dt>
              <MapPin /> Current department
            </dt>
            <dd>{patient.current_department?.name ?? 'Not assigned'}</dd>
          </div>
          <div>
            <dt>
              <FileText /> Medical file
            </dt>
            <dd>{patient.medical_file?.file_number ?? 'Not available'}</dd>
          </div>
          <div>
            <dt>
              <HeartHandshake /> Blood type
            </dt>
            <dd>{patient.blood_type || 'Not recorded'}</dd>
          </div>
        </dl>
      </section>
      <div className="patient-detail-grid">
        <section className="section-panel">
          <p className="eyebrow">Current episode</p>
          <h2>{patient.active_episode?.episode_type_label ?? 'No active episode'}</h2>
          {patient.active_episode ? (
            <dl className="detail-list">
              <div>
                <dt>Episode</dt>
                <dd>{patient.active_episode.episode_number}</dd>
              </div>
              <div>
                <dt>Admitted</dt>
                <dd>{new Date(patient.active_episode.admitted_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Reason</dt>
                <dd>{patient.active_episode.admission_reason}</dd>
              </div>
            </dl>
          ) : (
            <p className="muted-copy">No active care episode.</p>
          )}
        </section>
        <section className="section-panel">
          <p className="eyebrow">Care team</p>
          <h2>Active assignments</h2>
          <ul className="care-team-list">
            {patient.care_team.map((member) => (
              <li key={member.id}>
                <span>
                  <UsersRound />
                </span>
                <div>
                  <strong>{member.full_name}</strong>
                  <small>
                    {member.role.toLowerCase()} · {member.job_title || 'Clinical staff'}
                  </small>
                </div>
                {member.is_primary && <StatusBadge status="ACTIVE" label="Primary" />}
              </li>
            ))}
          </ul>
        </section>
        <section className="section-panel">
          <p className="eyebrow">Contact</p>
          <h2>Patient details</h2>
          <dl className="detail-list">
            <div>
              <dt>
                <Phone /> Patient telephone
              </dt>
              <dd>{patient.phone || 'Not provided'}</dd>
            </div>
            <div>
              <dt>Address</dt>
              <dd>{patient.address}</dd>
            </div>
            <div>
              <dt>Emergency contact</dt>
              <dd>
                {patient.emergency_contact_name} · {patient.emergency_contact_phone}
              </dd>
            </div>
          </dl>
        </section>
        <section className="section-panel">
          <p className="eyebrow">Authorized support</p>
          <h2>Patient Guard access</h2>
          <div className="guardian-count">
            <span>
              <ShieldCheck />
            </span>
            <strong>{patient.active_guardian_count}</strong>
            <p>active Patient Guard {patient.active_guardian_count === 1 ? 'relationship' : 'relationships'}</p>
          </div>
        </section>
      </div>
    </div>
  )
}
