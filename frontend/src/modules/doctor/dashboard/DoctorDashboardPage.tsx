import { useQuery } from '@tanstack/react-query'
import { ClipboardPlus, FileClock, HeartHandshake, ShieldAlert, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatientDashboard } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function DoctorDashboardPage() {
  const query = useQuery({ queryKey: ['patient-dashboard'], queryFn: getPatientDashboard })
  const data = query.data
  return <div className="workspace-page"><PageHeader eyebrow="Clinical workspace" title="Doctor dashboard" description="Your assigned patients and intake work, without unrelated hospital records." actions={<Link className="button button--primary" to="/doctor/patients/new"><ClipboardPlus size={17} /> Register patient</Link>} />{query.isPending && <SectionLoader />}{query.error && <Alert tone="critical">{query.error instanceof AppApiError ? query.error.message : 'Dashboard unavailable.'}</Alert>}{data && <><section className="metric-grid"><article className="metric-card"><span className="metric-card__icon metric-card__icon--blue"><UsersRound /></span><div><small>Assigned patients</small><strong>{data.total_assigned}</strong><p>Current care relationships</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--green"><FileClock /></span><div><small>Active episodes</small><strong>{data.active_episodes}</strong><p>Current episodes of care</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--red"><ShieldAlert /></span><div><small>Critical latest vitals</small><strong>{data.critical_patients}</strong><p>Patients requiring clinical review</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--amber"><HeartHandshake /></span><div><small>Without Patient Guard</small><strong>{data.without_guard}</strong><p>Patients needing support access</p></div></article></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Recently assigned</p><h2>Patients</h2></div><Link className="table-link" to="/doctor/patients">View all</Link></div><PatientTable patients={data.recent_patients} linkFor={(patient) => `/doctor/patients/${patient.id}`} emptyAction={<Link className="button button--primary" to="/doctor/patients/new">Register first patient</Link>} /></section></>}</div>
}
