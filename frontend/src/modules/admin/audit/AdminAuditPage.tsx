import { useQuery } from '@tanstack/react-query'
import { Search, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getAuditEvents } from '../users/api'

export function AdminAuditPage() {
  const [search, setSearch] = useState('')
  const query = useQuery({ queryKey: ['system-audit', search], queryFn: () => getAuditEvents(search) })
  return <div className="workspace-page"><PageHeader eyebrow="Security oversight" title="Redacted audit log" description="Review actors, actions and request identifiers. Clinical record bodies and snapshots are excluded." /><div className="list-toolbar"><label className="search-field"><Search size={17} /><span className="sr-only">Filter audit actions</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter by action" /></label><span>{query.data?.length ?? 0} events</span></div>{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Audit events could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No audit events found" description="Try a broader action filter." /></section> : <section className="audit-timeline">{query.data!.map((event) => <article key={event.id}><span><ShieldCheck /></span><div><strong>{event.action}</strong><p>{event.object_type} · {event.object_id || 'No object ID'}</p><small>{event.actor_name || 'System'} · {new Date(event.created_at).toLocaleString()} · Request {event.request_id || 'not available'}</small>{event.reason && <em>Reason: {event.reason}</em>}</div></article>)}</section>}</div>
}
