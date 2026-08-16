import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useState } from 'react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { PatientTable } from '../../patient-care/shared/PatientTable'

export function NursePatientsPage() {
  const [search, setSearch] = useState('')
  const query = useQuery({ queryKey: ['patients', 'nurse', search], queryFn: () => getPatients(search) })
  return <div className="workspace-page"><PageHeader eyebrow="Assigned care" title="My patients" description="Only patients with your active Nurse assignment are shown." /><div className="list-toolbar"><label className="search-field"><Search size={17} /><span className="sr-only">Search patients</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search name or medical record number" /></label><span>{query.data?.length ?? 0} patients</span></div><section className="section-panel table-panel">{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Unable to load assigned patients.</Alert> : <PatientTable patients={query.data ?? []} linkFor={(patient) => `/nurse/patients/${patient.id}`} />}</section></div>
}
