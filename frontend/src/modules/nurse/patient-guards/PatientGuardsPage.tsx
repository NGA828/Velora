import { useQuery } from '@tanstack/react-query'
import { ShieldAlert, ShieldCheck } from 'lucide-react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function PatientGuardsPage() {
  const query = useQuery({ queryKey: ['patients', 'nurse'], queryFn: () => getPatients() })
  const missing = query.data?.filter((patient) => patient.active_guardian_count === 0) ?? []
  return <div className="workspace-page"><PageHeader eyebrow="Authorized representatives" title="Patient Guard access" description="Invite and maintain the family member or representative authorized for each assigned patient." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Unable to load assigned patients.</Alert> : <><section className="summary-strip"><div><ShieldAlert /><span><small>Needs Patient Guard</small><strong>{missing.length}</strong></span></div><div><ShieldCheck /><span><small>Guard configured</small><strong>{(query.data?.length ?? 0) - missing.length}</strong></span></div></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Needs attention</p><h2>Patients without active Guard access</h2></div></div><PatientTable patients={missing} linkFor={(patient) => `/nurse/patients/${patient.id}`} /></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">All relationships</p><h2>Assigned patients</h2></div></div><PatientTable patients={query.data ?? []} linkFor={(patient) => `/nurse/patients/${patient.id}`} /></section></>}</div>
}
