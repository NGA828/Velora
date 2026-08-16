import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { ClinicalRecordWorkspace } from '../../clinical-records/shared/ClinicalRecordWorkspace'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'

export function PatientGuardMedicalFilePage() {
  const { patientId = '' } = useParams()
  const query = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return <div className="workspace-page"><div className="back-link"><Link to={`/patient-guard/patients/${patientId}`}><ArrowLeft size={16} /> Back to patient information</Link></div><PageHeader eyebrow="Released medical information" title={query.data ? `${query.data.full_name} · Medical file` : 'Medical file'} description="Only records released to your authorized Patient Guard access appear here." /><PatientPageState pending={query.isPending} error={query.error} />{query.data && <ClinicalRecordWorkspace patient={query.data} role="PATIENT_GUARD" />}</div>
}
