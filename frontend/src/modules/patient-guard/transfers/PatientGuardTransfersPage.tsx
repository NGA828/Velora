import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, CheckCircle2, XCircle } from 'lucide-react'
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
import { decideTransfer, getTransfers } from '../../transfers/shared/api'
import type { TransferRequest } from '../../transfers/shared/types'

export function PatientGuardTransfersPage() {
  const client = useQueryClient()
  const [selected, setSelected] = useState<TransferRequest | null>(null)
  const [decision, setDecision] = useState<'APPROVE' | 'REJECT'>('APPROVE')
  const [reason, setReason] = useState('')
  const query = useQuery({ queryKey: ['transfers', 'guard'], queryFn: () => getTransfers() })
  const mutation = useMutation({ mutationFn: () => decideTransfer(selected!.id, decision, reason), onSuccess: async () => { setSelected(null); await Promise.all([client.invalidateQueries({ queryKey: ['transfers'] }), client.invalidateQueries({ queryKey: ['notifications'] })]) } })
  const open = (transfer: TransferRequest, next: 'APPROVE' | 'REJECT') => { mutation.reset(); setSelected(transfer); setDecision(next); setReason('') }
  const pending = query.data?.filter((item) => item.status === 'PENDING_GUARDIAN').length ?? 0
  return <><div className="workspace-page"><PageHeader eyebrow="Transfer decisions" title="Transfer requests" description="Review the Doctor’s proposed destination and approve or reject the request assigned to you." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Transfer requests could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No transfer requests" description="Requests requiring your decision will appear here." /></section> : <><section className="summary-strip"><div><Building2 /><span><small>Awaiting decision</small><strong>{pending}</strong></span></div><div><CheckCircle2 /><span><small>Total requests</small><strong>{query.data?.length ?? 0}</strong></span></div></section><div className="transfer-list">{query.data!.map((transfer) => <article key={transfer.id} className="transfer-card"><header><div><span className="transfer-card__icon"><Building2 /></span><div><h2>{transfer.patient_name}</h2><p>{transfer.medical_record_number} · {transfer.urgency.toLowerCase()}</p></div></div><StatusBadge status={transfer.status} /></header><div className="transfer-summary"><div><strong>Doctor</strong><p>{transfer.requested_by_name}</p></div><div><strong>Proposed hospital</strong><p>{transfer.selected_hospital_name || 'Not selected'}</p></div><div><strong>Submitted</strong><p>{transfer.submitted_at ? new Date(transfer.submitted_at).toLocaleString() : 'Not submitted'}</p></div></div><section className="guard-transfer-clinical"><h3>Reason</h3><p>{transfer.reason}</p><h3>Clinical summary</h3><p>{transfer.clinical_summary}</p><h3>Required capabilities</h3><div className="requirement-chips">{transfer.requirements.map((item) => <span key={item.id}>{item.label_snapshot}{item.is_mandatory ? ' · mandatory' : ''}</span>)}</div></section>{transfer.decision && <Alert tone={transfer.decision.decision === 'APPROVE' ? 'success' : 'information'} title={`Decision: ${transfer.decision.decision.toLowerCase()}`}>{transfer.decision.reason || 'No additional reason provided.'}</Alert>}<footer>{transfer.status === 'PENDING_GUARDIAN' && <><Button onClick={() => open(transfer, 'APPROVE')}><CheckCircle2 size={16} /> Approve transfer</Button><Button variant="danger" onClick={() => open(transfer, 'REJECT')}><XCircle size={16} /> Reject</Button></>}</footer></article>)}</div></>}</div>
    <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title={decision === 'APPROVE' ? 'Approve transfer request?' : 'Reject transfer request?'} description={selected ? `${selected.patient_name} → ${selected.selected_hospital_name}` : undefined}><form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}><TextAreaField label={decision === 'REJECT' ? 'Reason for rejection' : 'Decision note (optional)'} required={decision === 'REJECT'} rows={4} value={reason} onChange={(e) => setReason(e.target.value)} />{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Decision could not be submitted.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setSelected(null)}>Cancel</Button><Button type="submit" variant={decision === 'APPROVE' ? 'primary' : 'danger'} isLoading={mutation.isPending}>{decision === 'APPROVE' ? 'Confirm approval' : 'Confirm rejection'}</Button></div></form></Modal>
  </>
}
