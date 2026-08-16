import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react'

import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { getVitalObservations } from './api'

const statusIcon = { STABLE: CheckCircle2, CRITICAL: AlertTriangle, UNASSESSED: HelpCircle }

export function VitalHistory({ patientId }: { patientId: string }) {
  const query = useQuery({ queryKey: ['vital-observations', patientId], queryFn: () => getVitalObservations(patientId) })
  if (query.isPending) return <section className="section-panel"><SectionLoader label="Loading vital history" /></section>
  if (query.error) return <Alert tone="critical">Vital-sign history could not be loaded.</Alert>
  if ((query.data?.length ?? 0) === 0) return <section className="section-panel"><EmptyState title="No vital observations" description="Vital-sign measurements recorded by the assigned Nurse will appear here." /></section>
  return <div className="vital-history">{query.data!.map((observation, index) => { const Icon = statusIcon[observation.status]; const matched = observation.values.flatMap((value) => value.evaluations).filter((evaluation) => evaluation.matched); return <article key={observation.id} className={`vital-observation vital-observation--${observation.status.toLowerCase()}`}><header><span className="vital-observation__icon"><Icon /></span><div><div><h2>{index === 0 ? 'Latest observation' : 'Observation'}</h2><StatusBadge status={observation.status} /></div><p>{new Date(observation.observed_at).toLocaleString()} · {observation.recorded_by_name}</p></div></header><div className="vital-values">{observation.values.map((value) => <div key={value.id}><small>{value.metric_name}</small><strong>{Number(value.value).toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong><span>{value.unit}</span></div>)}</div>{observation.status === 'UNASSESSED' && <Alert tone="information" title="Not assessed">No complete active rule coverage was available for every submitted metric. Velora did not assume a Stable result.</Alert>}{matched.length > 0 && <div className="evaluation-explanations"><strong><Activity size={16} /> Matched configured rules</strong>{matched.map((evaluation) => <p key={evaluation.id}>{evaluation.explanation}<small>{evaluation.rule_name_snapshot} · {evaluation.metric_name_snapshot}</small></p>)}</div>}{observation.notes && <p className="observation-notes"><strong>Nurse note:</strong> {observation.notes}</p>}<footer>{observation.rule_set_name_snapshot ? `Analyzed with ${observation.rule_set_name_snapshot} v${observation.rule_set_version_snapshot}` : 'No active approved rule set'}</footer></article>})}</div>
}
