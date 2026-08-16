import { useQuery } from '@tanstack/react-query'
import { BedDouble, Building2, CircleAlert, Hospital, UserRoundCheck, UserRoundPlus } from 'lucide-react'
import { Link } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getRecord } from '../shared/api'
import type { HospitalDashboard } from '../shared/types'

export function HeadOfServiceDashboardPage() {
  const query = useQuery({
    queryKey: ['head-of-service', 'dashboard'],
    queryFn: () => getRecord<HospitalDashboard>('/hospital/dashboard/'),
  })

  const data = query.data
  const attention = data ? [
    !data.hospital_profile_configured ? { text: 'Hospital profile needs to be configured', to: '/head-of-service/hospital-information' } : null,
    data.staff.pending_invitations > 0 ? { text: `${data.staff.pending_invitations} staff invitation${data.staff.pending_invitations === 1 ? '' : 's'} awaiting acceptance`, to: '/head-of-service/personnel' } : null,
    data.operations.resources_unavailable > 0 ? { text: `${data.operations.resources_unavailable} resource${data.operations.resources_unavailable === 1 ? '' : 's'} unavailable or in maintenance`, to: '/head-of-service/resources' } : null,
    data.transfers.incomplete_profiles > 0 ? { text: `${data.transfers.incomplete_profiles} external hospital profile${data.transfers.incomplete_profiles === 1 ? '' : 's'} incomplete for transfer`, to: '/head-of-service/external-hospitals' } : null,
  ].filter(Boolean) as { text: string; to: string }[] : []

  return <div className="workspace-page">
    <PageHeader eyebrow="Hospital operations" title="Head of Service dashboard" description="The configuration and staffing items that need attention now." actions={<Link className="button button--primary" to="/head-of-service/personnel"><UserRoundPlus size={17} /> Invite staff</Link>} />
    {query.isPending && <SectionLoader />}
    {query.error && <Alert tone="critical" title="Dashboard unavailable">{query.error instanceof AppApiError ? query.error.message : 'Try again.'}</Alert>}
    {data && <>
      <section className="metric-grid" aria-label="Hospital configuration summary">
        <article className="metric-card"><span className="metric-card__icon metric-card__icon--blue"><UserRoundCheck /></span><div><small>Active clinical staff</small><strong>{data.staff.active_clinical}</strong><p>Doctors and nurses</p></div></article>
        <article className="metric-card"><span className="metric-card__icon metric-card__icon--teal"><Building2 /></span><div><small>Active departments</small><strong>{data.operations.departments}</strong><p>Configured services</p></div></article>
        <article className="metric-card"><span className="metric-card__icon metric-card__icon--green"><BedDouble /></span><div><small>Available beds</small><strong>{data.operations.available_beds}<em>/{data.operations.total_beds}</em></strong><p>Current directory status</p></div></article>
        <article className="metric-card"><span className="metric-card__icon metric-card__icon--amber"><Hospital /></span><div><small>Transfer hospitals</small><strong>{data.transfers.external_hospitals}</strong><p>Active directory records</p></div></article>
      </section>
      <div className="dashboard-columns">
        <section className="section-panel attention-panel">
          <div className="section-panel__heading"><div><p className="eyebrow">Attention</p><h2>Configuration requiring action</h2></div><span>{attention.length} items</span></div>
          {attention.length === 0 ? <div className="all-clear"><span><UserRoundCheck /></span><div><strong>Configuration is up to date</strong><p>No setup issues currently need attention.</p></div></div> : <ul className="attention-list">{attention.map((item) => <li key={item.text}><CircleAlert /><span>{item.text}</span><Link to={item.to}>Review</Link></li>)}</ul>}
        </section>
        <section className="section-panel quick-links-panel"><p className="eyebrow">Next actions</p><h2>Hospital setup</h2><nav aria-label="Hospital setup shortcuts"><Link to="/head-of-service/hospital-information">Hospital & departments <span>→</span></Link><Link to="/head-of-service/specialties">Specialties & conditions <span>→</span></Link><Link to="/head-of-service/resources">Resources & services <span>→</span></Link><Link to="/head-of-service/clinical-rules">Vital analysis rules <span>→</span></Link></nav></section>
      </div>
    </>}
  </div>
}
