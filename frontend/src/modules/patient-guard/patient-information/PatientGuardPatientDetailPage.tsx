import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText, LockKeyhole } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatient } from '../../patient-care/shared/api'
import { PatientOverview } from '../../patient-care/shared/PatientOverview'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'

export function PatientGuardPatientDetailPage() {
  const { patientId = '' } = useParams()
  const query = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return <div className="workspace-page"><div className="back-link"><Link to="/patient-guard/patients"><ArrowLeft size={16} /> Back to linked patients</Link></div><PageHeader eyebrow="Authorized patient record" title={query.data?.full_name ?? 'Patient information'} description={query.data ? `${query.data.medical_record_number} · Visible through your active Patient Guard relationship.` : 'Loading authorized information.'} actions={query.data?.medical_file && <Link className="button button--secondary" to={`/patient-guard/patients/${patientId}/medical-file`}><FileText size={16} /> Medical file</Link>} /><Alert tone="information" title="Your privacy boundary"><LockKeyhole size={16} /> Internal clinical notes and unapproved information are not exposed through this view.</Alert><PatientPageState pending={query.isPending} error={query.error} />{query.data && <PatientOverview patient={query.data} />}</div>
}
