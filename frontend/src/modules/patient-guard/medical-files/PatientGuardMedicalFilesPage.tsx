import { useQuery } from '@tanstack/react-query'
import { FileText } from 'lucide-react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function PatientGuardMedicalFilesPage() {
  const query = useQuery({ queryKey: ['patients', 'guard'], queryFn: () => getPatients() })
  return <div className="workspace-page"><PageHeader eyebrow="Released clinical information" title="Medical files" description="Open medical-file information released for each linked patient." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Released medical files could not be loaded.</Alert> : <section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Authorized records</p><h2>Linked patients</h2></div><FileText /></div><PatientTable patients={query.data ?? []} linkFor={(patient) => `/patient-guard/patients/${patient.id}/medical-file`} /></section>}</div>
}
