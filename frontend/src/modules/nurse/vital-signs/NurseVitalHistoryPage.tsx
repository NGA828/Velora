import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Plus } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { VitalHistory } from '../../vital-signs/shared/VitalHistory'

export function NurseVitalHistoryPage() {
  const { patientId = '' } = useParams()
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return <div className="workspace-page"><div className="back-link"><Link to={`/nurse/patients/${patientId}`}><ArrowLeft size={16} /> Back to patient overview</Link></div><PageHeader eyebrow="Patient monitoring" title={patient.data ? `${patient.data.full_name} · Vital history` : 'Vital history'} description="Measurements, stability or criticality percentage, and the configured explanations used at the time." actions={<Link className="button button--primary" to={`/nurse/patients/${patientId}/vitals/new`}><Plus size={16} /> Record vitals</Link>} /><PatientPageState pending={patient.isPending} error={patient.error} />{patient.data && <VitalHistory patientId={patientId} />}</div>
}
