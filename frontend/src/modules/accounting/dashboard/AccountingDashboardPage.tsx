import { useQuery } from '@tanstack/react-query'
import { Banknote, Clock3, FileText, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getBillingDashboard } from '../../billing/shared/api'
import { formatMoney } from '../../billing/shared/format'

export function AccountingDashboardPage() {
  const query = useQuery({ queryKey: ['billing-dashboard'], queryFn: getBillingDashboard })
  const data = query.data
  return <div className="workspace-page"><PageHeader eyebrow="Financial operations" title="Accounting dashboard" description="Invoices, collections and exceptions requiring financial attention." actions={<Link className="button button--primary" to="/accounting/billing">Manage billing</Link>} />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Billing dashboard could not be loaded.</Alert> : data && <><section className="metric-grid"><article className="metric-card"><span className="metric-card__icon metric-card__icon--blue"><FileText /></span><div><small>Draft invoices</small><strong>{data.draft_invoices}</strong><p>Not yet issued</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--amber"><Clock3 /></span><div><small>Outstanding</small><strong>{formatMoney(data.outstanding_amount, data.currency)}</strong><p>Issued balance</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--red"><TriangleAlert /></span><div><small>Overdue invoices</small><strong>{data.overdue_invoices}</strong><p>Past due and unpaid</p></div></article><article className="metric-card"><span className="metric-card__icon metric-card__icon--green"><Banknote /></span><div><small>Payments today</small><strong>{formatMoney(data.payments_today, data.currency)}</strong><p>Posted collections</p></div></article></section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Recent activity</p><h2>Invoices</h2></div><Link className="table-link" to="/accounting/billing">View all</Link></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Invoice</th><th>Patient</th><th>Status</th><th>Total</th><th>Outstanding</th></tr></thead><tbody>{data.recent_invoices.map((invoice) => <tr key={invoice.id}><td><strong>{invoice.invoice_number}</strong><small>{invoice.issued_at ? new Date(invoice.issued_at).toLocaleDateString() : 'Draft'}</small></td><td>{invoice.patient_name}<small>{invoice.medical_record_number}</small></td><td>{invoice.status}</td><td>{formatMoney(invoice.total, invoice.currency)}</td><td>{formatMoney(invoice.outstanding_amount, invoice.currency)}</td></tr>)}</tbody></table></div></section></>}</div>
}
