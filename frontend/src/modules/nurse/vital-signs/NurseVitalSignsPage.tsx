import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function NurseVitalSignsPage() {
  const query = useQuery({ queryKey: ['patients', 'nurse'], queryFn: () => getPatients() })
  return <div className="workspace-page"><PageHeader eyebrow="Patient monitoring" title="Vital signs" description="Open an assigned patient to record measurements or review previous evaluations." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Assigned patients could not be loaded.</Alert> : <section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Assigned patients</p><h2>Monitoring status</h2></div><Activity /></div><PatientTable patients={query.data ?? []} linkFor={(patient) => `/nurse/patients/${patient.id}/vitals`} /><div className="table-footer-note">To record a new observation, open vital history and select “Record vitals”.</div></section>}</div>
}
