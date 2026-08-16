import { useQuery } from '@tanstack/react-query'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function PatientInformationPage() {
  const query = useQuery({ queryKey: ['patients', 'guard'], queryFn: () => getPatients() })
  return <div className="workspace-page"><PageHeader eyebrow="Authorized information" title="Patient information" description="Every patient shown here has an active Patient Guard relationship to your account." /><section className="section-panel table-panel">{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Unable to load linked patients.</Alert> : <PatientTable patients={query.data ?? []} linkFor={(patient) => `/patient-guard/patients/${patient.id}`} />}</section></div>
}
