import { useQuery } from '@tanstack/react-query'
import { Building2, HeartHandshake, HelpCircle, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getMonitoringThreads } from '../../monitoring/shared/api'
import { getPatientDashboard } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'
import { getTransfers } from '../../transfers/shared/api'

export function PatientGuardDashboardPage() {
  const query = useQuery({ queryKey: ['patient-dashboard'], queryFn: getPatientDashboard })
  const monitoring = useQuery({ queryKey: ['monitoring-threads', 'guard'], queryFn: () => getMonitoringThreads() })
  const transfers = useQuery({ queryKey: ['transfers', 'guard'], queryFn: () => getTransfers() })
  const data = query.data
  const pendingQuestions = monitoring.data?.reduce((count, thread) => count + thread.pending_question_count, 0) ?? 0
  const pendingTransfers = transfers.data?.filter((item) => item.status === 'PENDING_GUARDIAN').length ?? 0
  return <div className="workspace-page"><PageHeader eyebrow="Patient support" title="Patient Guard dashboard" description="Only patients explicitly linked to your account are shown." />{query.isPending && <SectionLoader />}{query.error && <Alert tone="critical">Unable to load authorized patient information.</Alert>}{data && <><section className="welcome-panel guard-welcome"><div className="welcome-panel__copy"><span className="welcome-panel__icon"><HeartHandshake /></span><div><p className="eyebrow eyebrow--light">Authorized access</p><h2>Supporting {data.total_assigned} linked {data.total_assigned === 1 ? 'patient' : 'patients'}.</h2><p>Your access is limited to the information and decisions authorized for each patient relationship.</p></div></div><div className="welcome-panel__facts"><div><ShieldCheck /><span><small>Access model</small><strong>Explicit Patient Guard link</strong></span></div></div></section><section className="summary-strip"><div><HelpCircle /><span><small>Monitoring responses due</small><strong>{pendingQuestions}</strong></span></div><div><Building2 /><span><small>Transfer decisions due</small><strong>{pendingTransfers}</strong></span></div></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Patient information</p><h2>Linked patients</h2></div><Link className="table-link" to="/patient-guard/patients">View all</Link></div><PatientTable patients={data.recent_patients} linkFor={(patient) => `/patient-guard/patients/${patient.id}`} /></section></>}</div>
}
