import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { ClinicalRecordWorkspace } from '../../clinical-records/shared/ClinicalRecordWorkspace'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'

export function NurseMedicalFilePage() {
  const { patientId = '' } = useParams()
  const query = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return <div className="workspace-page"><div className="back-link"><Link to={`/nurse/patients/${patientId}`}><ArrowLeft size={16} /> Back to patient overview</Link></div><PageHeader eyebrow="Care-relevant record" title={query.data ? `${query.data.full_name} · Medical file` : 'Medical file'} description="Review authorized clinical history and add nursing documentation." /><PatientPageState pending={query.isPending} error={query.error} />{query.data && <ClinicalRecordWorkspace patient={query.data} role="NURSE" />}</div>
}
