import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Banknote, RotateCcw } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { FormField } from '../../../shared/ui/forms/FormField'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { createPayment, getInvoices, getPayments, reversePayment } from '../../billing/shared/api'
import { formatMoney } from '../../billing/shared/format'
import type { Payment } from '../../billing/shared/types'

export function PaymentsPage() {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('CASH')
  const [reference, setReference] = useState('')
  const [reversing, setReversing] = useState<Payment | null>(null)
  const [reason, setReason] = useState('')
  const payments = useQuery({ queryKey: ['payments'], queryFn: getPayments })
  const invoices = useQuery({ queryKey: ['invoices'], queryFn: () => getInvoices() })
  const payable = invoices.data?.filter((item) => ['ISSUED', 'PARTIALLY_PAID'].includes(item.status)) ?? []
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ['payments'] }), client.invalidateQueries({ queryKey: ['invoices'] }), client.invalidateQueries({ queryKey: ['billing-dashboard'] })])
  const createMutation = useMutation({ mutationFn: () => createPayment({ invoice: invoiceId, amount, method, reference }), onSuccess: async () => { setOpen(false); await refresh() } })
  const reverseMutation = useMutation({ mutationFn: () => reversePayment(reversing!.id, reason), onSuccess: async () => { setReversing(null); await refresh() } })
  const chooseInvoice = (id: string) => { setInvoiceId(id); const invoice = payable.find((item) => item.id === id); setAmount(invoice?.outstanding_amount ?? '') }
  return <div className="workspace-page"><PageHeader eyebrow="Collections" title="Payments and receipts" description="Post payments against issued invoices and reverse errors without deleting financial history." actions={<Button disabled={payable.length === 0} onClick={() => { setOpen(true); setInvoiceId(''); setAmount(''); setReference('') }}><Banknote size={16} /> Record payment</Button>} />{payments.isPending ? <SectionLoader /> : payments.error ? <Alert tone="critical">Payment history could not be loaded.</Alert> : (payments.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No payments recorded" description="Payments can be posted after an invoice is issued." /></section> : <section className="section-panel table-panel"><div className="table-scroll"><table className="data-table"><thead><tr><th>Receipt</th><th>Invoice</th><th>Amount</th><th>Method</th><th>Received</th><th>Status</th><th /></tr></thead><tbody>{payments.data!.map((payment) => <tr key={payment.id}><td><strong>{payment.receipt_number}</strong><small>{payment.reference || 'No reference'}</small></td><td><strong>{payment.invoice_number}</strong><small>{payment.patient_name}</small></td><td>{formatMoney(payment.amount, payment.currency)}</td><td>{payment.method.toLowerCase().replaceAll('_', ' ')}</td><td>{new Date(payment.received_at).toLocaleString()}<small>{payment.recorded_by_name}</small></td><td><StatusBadge status={payment.status} /></td><td>{payment.status === 'POSTED' && <Button variant="ghost" onClick={() => { setReversing(payment); setReason('') }}><RotateCcw size={15} /> Reverse</Button>}</td></tr>)}</tbody></table></div></section>}
    <Modal open={open} onClose={() => setOpen(false)} title="Record payment" description="The amount cannot exceed the selected invoice’s outstanding balance."><form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }}><SelectField label="Invoice" required value={invoiceId} onChange={(e) => chooseInvoice(e.target.value)}><option value="">Select outstanding invoice</option>{payable.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {invoice.patient_name} · {formatMoney(invoice.outstanding_amount, invoice.currency)}</option>)}</SelectField><div className="form-grid"><FormField label="Amount" type="number" min="0.01" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} /><SelectField label="Payment method" value={method} onChange={(e) => setMethod(e.target.value)}><option value="CASH">Cash</option><option value="CARD">Card</option><option value="BANK_TRANSFER">Bank transfer</option><option value="MOBILE_MONEY">Mobile money</option><option value="OTHER">Other</option></SelectField></div><FormField label="Provider or transaction reference" value={reference} onChange={(e) => setReference(e.target.value)} />{createMutation.error && <Alert tone="critical">{createMutation.error instanceof AppApiError ? createMutation.error.message : 'Payment could not be posted.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" isLoading={createMutation.isPending}>Post payment</Button></div></form></Modal>
    <Modal open={Boolean(reversing)} onClose={() => setReversing(null)} title="Reverse payment" description="The original receipt remains in financial history."><form onSubmit={(event) => { event.preventDefault(); reverseMutation.mutate() }}><TextAreaField label="Reversal reason" required rows={4} value={reason} onChange={(e) => setReason(e.target.value)} />{reverseMutation.error && <Alert tone="critical">{reverseMutation.error instanceof AppApiError ? reverseMutation.error.message : 'Payment could not be reversed.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setReversing(null)}>Cancel</Button><Button type="submit" variant="danger" isLoading={reverseMutation.isPending}>Reverse payment</Button></div></form></Modal>
  </div>
}
