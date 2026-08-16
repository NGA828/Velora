import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pill, Plus } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { FormField } from '../../../shared/ui/forms/FormField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { createMedication, getMedications, updateMedication } from '../../prescriptions/shared/api'
import type { Medication } from '../../prescriptions/shared/types'

const blank = { generic_name: '', brand_name: '', form: '', strength: '', description: '', is_active: true }

export function MedicationsPage() {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Medication | null>(null)
  const [form, setForm] = useState(blank)
  const query = useQuery({ queryKey: ['medications'], queryFn: () => getMedications() })
  const mutation = useMutation({
    mutationFn: () => editing ? updateMedication(editing.id, form) : createMedication(form),
    onSuccess: async () => { setOpen(false); setEditing(null); await client.invalidateQueries({ queryKey: ['medications'] }) },
  })
  const show = (item?: Medication) => { mutation.reset(); setEditing(item ?? null); setForm(item ? { generic_name: item.generic_name, brand_name: item.brand_name, form: item.form, strength: item.strength, description: item.description, is_active: item.is_active } : blank); setOpen(true) }
  return <div className="workspace-page"><PageHeader eyebrow="Medication catalogue" title="Hospital medications" description="Maintain the medication vocabulary Doctors use when creating prescriptions." actions={<Button onClick={() => show()}><Plus size={16} /> Add medication</Button>} />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Medication catalogue could not be loaded.</Alert> : <section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Reference catalogue</p><h2>Medications</h2></div><span>{query.data?.length ?? 0} entries</span></div>{(query.data?.length ?? 0) === 0 ? <EmptyState title="No medications configured" description="Add a medication before Doctors can prescribe it." action={<Button onClick={() => show()}>Add medication</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Medication</th><th>Brand</th><th>Strength</th><th>Form</th><th>Status</th><th /></tr></thead><tbody>{query.data!.map((item) => <tr key={item.id}><td><strong>{item.generic_name}</strong><small>{item.description || 'No description'}</small></td><td>{item.brand_name || 'Generic'}</td><td>{item.strength}</td><td>{item.form}</td><td><StatusBadge status={item.is_active ? 'ACTIVE' : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => show(item)}>Edit</Button></td></tr>)}</tbody></table></div>}</section>}<Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit medication' : 'Add medication'} description="Medication entries define identity only; dosage and schedule belong to each prescription."><form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}><FormField label="Generic name" required value={form.generic_name} onChange={(e) => setForm({ ...form, generic_name: e.target.value })} /><FormField label="Brand name (optional)" value={form.brand_name} onChange={(e) => setForm({ ...form, brand_name: e.target.value })} /><div className="form-grid"><FormField label="Strength" required placeholder="For example: 10 mg" value={form.strength} onChange={(e) => setForm({ ...form, strength: e.target.value })} /><FormField label="Form" required placeholder="For example: Tablet" value={form.form} onChange={(e) => setForm({ ...form, form: e.target.value })} /></div><TextAreaField label="Description" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /><label className="check-field"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /><span><strong>Medication is available for new prescriptions</strong></span></label>{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Medication could not be saved.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" isLoading={mutation.isPending}><Pill size={16} /> Save medication</Button></div></form></Modal></div>
}
