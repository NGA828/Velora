import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ClipboardList, Pill, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatientDashboard } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'
import { getDueDoses } from '../../prescriptions/shared/api'

export function NurseDashboardPage() {
  const query = useQuery({ queryKey: ['patient-dashboard'], queryFn: getPatientDashboard })
  const due = useQuery({ queryKey: ['medication-doses', 'due'], queryFn: getDueDoses })
  const data = query.data
  return <div className="workspace-page"><PageHeader eyebrow="Care delivery" title="Nurse dashboard" description="Assigned patients and Patient Guard setup requiring your attention." actions={<Link className="button button--secondary" to="/nurse/patient-guards"><ShieldAlert size={17} /> Patient Guards</Link>} />{query.isPending && <SectionLoader />}{query.error && <Alert tone="critical">{query.error instanceof AppApiError ? query.error.message : 'Dashboard unavailable.'}</Alert>}{data && <><section className="metric-grid"><article className="metric-card"><span className="metric-card__icon metric-card__icon--blue"><ClipboardList /></span><div><small>Assigned patients</small><strong>{data.total_assigned}</strong><p>Active Nurse relationships</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--green"><Pill /></span><div><small>Medication due</small><strong>{due.data?.length ?? 0}</strong><p>Pending in the next 24 hours</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--red"><AlertTriangle /></span><div><small>Critical latest vitals</small><strong>{data.critical_patients}</strong><p>Doctor notification generated</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--amber"><ShieldAlert /></span><div><small>Without Patient Guard</small><strong>{data.without_guard}</strong><p>Representatives still to invite</p></div></article></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Recently assigned</p><h2>My patients</h2></div><Link className="table-link" to="/nurse/patients">View all</Link></div><PatientTable patients={data.recent_patients} linkFor={(patient) => `/nurse/patients/${patient.id}`} /></section></>}</div>
}
