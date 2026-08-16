import { useQuery } from '@tanstack/react-query'
import { ReceiptText } from 'lucide-react'

import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getInvoices } from '../../billing/shared/api'
import { formatMoney } from '../../billing/shared/format'

export function PatientGuardBillingPage() {
  const query = useQuery({ queryKey: ['invoices', 'guard'], queryFn: () => getInvoices() })
  return <div className="workspace-page"><PageHeader eyebrow="Authorized billing" title="Invoices" description="Only invoices explicitly authorized through your Patient Guard relationship are shown." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Billing information could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No billing access or invoices" description="Billing information appears only when the hospital grants this permission for a linked patient." /></section> : <div className="invoice-list">{query.data!.map((invoice) => <article key={invoice.id} className="invoice-card"><header><div><span><ReceiptText /></span><div><h2>{invoice.invoice_number}</h2><p>{invoice.patient_name} · {invoice.medical_record_number}</p></div></div><StatusBadge status={invoice.status} /></header><div className="invoice-lines">{invoice.lines.map((line) => <div key={line.id}><span><strong>{line.description}</strong><small>{line.quantity} × {formatMoney(line.unit_price, invoice.currency)}</small></span><strong>{formatMoney(line.line_total, invoice.currency)}</strong></div>)}</div><div className="invoice-totals"><span>Paid <strong>{formatMoney(invoice.amount_paid, invoice.currency)}</strong></span><span>Outstanding <strong>{formatMoney(invoice.outstanding_amount, invoice.currency)}</strong></span><span>Total <strong>{formatMoney(invoice.total, invoice.currency)}</strong></span></div></article>)}</div>}</div>
}
