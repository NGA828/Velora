import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Clock3, Pill, XCircle } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { getDueDoses, getMedicationDoses, recordDoseOutcome } from '../../prescriptions/shared/api'
import type { MedicationDose } from '../../prescriptions/shared/types'

type Outcome = 'administer' | 'miss' | 'refuse'

export function MedicationPage() {
  const client = useQueryClient()
  const [tab, setTab] = useState<'due' | 'history'>('due')
  const [selected, setSelected] = useState<MedicationDose | null>(null)
  const [outcome, setOutcome] = useState<Outcome>('administer')
  const [notes, setNotes] = useState('')
  const due = useQuery({ queryKey: ['medication-doses', 'due'], queryFn: getDueDoses, refetchInterval: 60_000 })
  const history = useQuery({ queryKey: ['medication-doses', 'history'], queryFn: () => getMedicationDoses() })
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ['medication-doses'] }), client.invalidateQueries({ queryKey: ['notifications'] }), client.invalidateQueries({ queryKey: ['prescriptions'] })])
  const mutation = useMutation({ mutationFn: () => recordDoseOutcome(selected!.id, outcome, notes), onSuccess: async () => { setSelected(null); setNotes(''); await refresh() } })
  const open = (dose: MedicationDose, nextOutcome: Outcome) => { mutation.reset(); setSelected(dose); setOutcome(nextOutcome); setNotes('') }
  const doses = tab === 'due' ? due.data ?? [] : (history.data ?? []).filter((dose) => dose.status !== 'PENDING')
  const pending = tab === 'due' ? due.isPending : history.isPending
  const failed = tab === 'due' ? due.isError : history.isError
  const overdue = (due.data ?? []).filter((dose) => dose.is_overdue).length
  return <div className="workspace-page"><PageHeader eyebrow="Medication administration" title="Medication queue" description="Confirm each scheduled dose against the active Doctor prescription and preserve actual outcome time." /><section className="summary-strip"><div><Clock3 /><span><small>Due in next 24 hours</small><strong>{due.data?.length ?? 0}</strong></span></div><div><AlertTriangle /><span><small>Overdue pending</small><strong>{overdue}</strong></span></div><div><CheckCircle2 /><span><small>Resolved records</small><strong>{(history.data ?? []).filter((dose) => dose.status !== 'PENDING').length}</strong></span></div></section><div className="tabs"><button className={tab === 'due' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('due')}>Due queue <span>{due.data?.length ?? 0}</span></button><button className={tab === 'history' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('history')}>Administration history</button></div>{pending ? <SectionLoader /> : failed ? <Alert tone="critical">Medication records could not be loaded.</Alert> : doses.length === 0 ? <section className="section-panel"><EmptyState title={tab === 'due' ? 'No medication doses due' : 'No administration history'} description={tab === 'due' ? 'Pending doses appear here during the 24 hours before their scheduled time.' : 'Administered, missed and refused events appear here.'} /></section> : <div className="dose-list">{doses.map((dose) => <article key={dose.id} className={dose.is_overdue ? 'dose-card dose-card--overdue' : 'dose-card'}><div className="dose-card__time"><Clock3 /><strong>{new Date(dose.scheduled_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong><small>{new Date(dose.scheduled_for).toLocaleDateString()}</small>{dose.is_overdue && <StatusBadge status="CRITICAL" label="Overdue" />}</div><div className="dose-card__content"><div><span className="prescription-card__icon"><Pill /></span><div><h2>{dose.medication_name}</h2><p>{Number(dose.dose_amount)} {dose.dose_unit} · {dose.route.toLowerCase()}</p></div></div><dl><div><dt>Patient</dt><dd>{dose.patient_name}<small>{dose.medical_record_number}</small></dd></div><div><dt>Instructions</dt><dd>{dose.instructions || 'No item-specific instructions'}</dd></div>{dose.actual_at && <div><dt>Actual time</dt><dd>{new Date(dose.actual_at).toLocaleString()}<small>{dose.acted_by_name}</small></dd></div>}</dl>{dose.notes && <p className="observation-notes"><strong>Notes:</strong> {dose.notes}</p>}</div><div className="dose-card__actions">{dose.status === 'PENDING' ? <><Button onClick={() => open(dose, 'administer')}><CheckCircle2 size={16} /> Administer</Button><Button variant="secondary" onClick={() => open(dose, 'refuse')}><XCircle size={16} /> Refused</Button><Button variant="ghost" onClick={() => open(dose, 'miss')}>Mark missed</Button></> : <StatusBadge status={dose.status} />}</div></article>)}</div>}<Modal open={Boolean(selected)} onClose={() => setSelected(null)} title={outcome === 'administer' ? 'Confirm administration' : outcome === 'refuse' ? 'Record refused dose' : 'Record missed dose'} description={selected ? `${selected.medication_name} · ${selected.patient_name}` : undefined}><form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>{selected && <div className="dose-confirmation"><div><small>Scheduled time</small><strong>{new Date(selected.scheduled_for).toLocaleString()}</strong></div><div><small>Dose</small><strong>{Number(selected.dose_amount)} {selected.dose_unit}</strong></div></div>}<TextAreaField label={outcome === 'administer' ? 'Administration notes (optional)' : 'Reason and notes'} required={outcome !== 'administer'} rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} />{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Outcome could not be saved.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setSelected(null)}>Cancel</Button><Button type="submit" variant={outcome === 'administer' ? 'primary' : 'danger'} isLoading={mutation.isPending}>{outcome === 'administer' ? 'Confirm administered' : outcome === 'refuse' ? 'Confirm refused' : 'Confirm missed'}</Button></div></form></Modal></div>
}
