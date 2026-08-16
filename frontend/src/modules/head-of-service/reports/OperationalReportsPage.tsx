import { useQuery } from '@tanstack/react-query'
import { BedDouble, Building2, Hospital, UsersRound } from 'lucide-react'

import { apiClient } from '../../../shared/api/client'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'

interface OperationalReport { generated_at: string; staff: { doctors: number; nurses: number }; patients: { total: number; registered_last_30_days: number; by_status: { status: string; count: number }[] }; operations: { departments: number; beds_available: number; beds_total: number; resources_unavailable: number; external_hospitals: number } }

export function OperationalReportsPage() {
  const query = useQuery({ queryKey: ['operational-report'], queryFn: async () => (await apiClient.get<OperationalReport>('/reports/operational/')).data })
  const data = query.data
  return <div className="workspace-page"><PageHeader eyebrow="Hospital reporting" title="Operational report" description="Aggregate staffing, patient and resource information without opening clinical records." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Operational report could not be generated.</Alert> : data && <><section className="metric-grid"><article className="metric-card"><span className="metric-card__icon metric-card__icon--blue"><UsersRound /></span><div><small>Clinical personnel</small><strong>{data.staff.doctors + data.staff.nurses}</strong><p>{data.staff.doctors} Doctors · {data.staff.nurses} Nurses</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--green"><Hospital /></span><div><small>Patients</small><strong>{data.patients.total}</strong><p>{data.patients.registered_last_30_days} registered in 30 days</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--teal"><BedDouble /></span><div><small>Available beds</small><strong>{data.operations.beds_available}/{data.operations.beds_total}</strong><p>Directory availability</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--amber"><Building2 /></span><div><small>External hospitals</small><strong>{data.operations.external_hospitals}</strong><p>{data.operations.resources_unavailable} unavailable resources</p></div></article></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Patient operations</p><h2>Care status distribution</h2></div></div><table className="data-table"><thead><tr><th>Status</th><th>Patients</th></tr></thead><tbody>{data.patients.by_status.map((item) => <tr key={item.status}><td>{item.status.replaceAll('_', ' ').toLowerCase()}</td><td>{item.count}</td></tr>)}</tbody></table></section></>}</div>
}
