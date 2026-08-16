import { useQuery } from '@tanstack/react-query'
import { FileText } from 'lucide-react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function DoctorMedicalFilesPage() {
  const query = useQuery({ queryKey: ['patients', 'doctor'], queryFn: () => getPatients() })
  return <div className="workspace-page"><PageHeader eyebrow="Clinical records" title="Medical files" description="Open the longitudinal record for a patient in your active care assignment." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Medical files could not be loaded.</Alert> : <section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Assigned records</p><h2>Patient medical files</h2></div><FileText /></div><PatientTable patients={query.data ?? []} linkFor={(patient) => `/doctor/patients/${patient.id}/medical-file`} /></section>}</div>
}
