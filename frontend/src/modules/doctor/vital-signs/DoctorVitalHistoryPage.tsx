import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { VitalHistory } from '../../vital-signs/shared/VitalHistory'

export function DoctorVitalHistoryPage() {
  const { patientId = '' } = useParams()
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return <div className="workspace-page"><div className="back-link"><Link to={`/doctor/patients/${patientId}`}><ArrowLeft size={16} /> Back to patient overview</Link></div><PageHeader eyebrow="Clinical monitoring" title={patient.data ? `${patient.data.full_name} · Vital history` : 'Vital history'} description="Review the actual measurements and explainable result stored for each observation." /><PatientPageState pending={patient.isPending} error={patient.error} />{patient.data && <VitalHistory patientId={patientId} />}</div>
}
