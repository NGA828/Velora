import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch, Pencil, Plus, Stethoscope } from 'lucide-react'
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
import { createRecord, listRecords, updateRecord } from '../shared/api'
import type { ClinicalCondition, Specialty, SpecialtyMapping } from '../shared/types'

type Tab = 'specialties' | 'conditions' | 'mappings'
type Dialog = { type: Tab; item?: Specialty | ClinicalCondition | SpecialtyMapping } | null

export function SpecialtiesPage() {
  const client = useQueryClient()
  const [tab, setTab] = useState<Tab>('specialties')
  const [dialog, setDialog] = useState<Dialog>(null)
  const [specialtyForm, setSpecialtyForm] = useState({ code: '', name: '', description: '', is_active: true })
  const [conditionForm, setConditionForm] = useState({ coding_system: 'LOCAL', code: '', name: '', description: '', is_active: true })
  const [mappingForm, setMappingForm] = useState({ specialty: '', condition: '', match_weight: '1.00', notes: '' })
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: () => listRecords<Specialty>('/hospital/specialties/') })
  const conditions = useQuery({ queryKey: ['conditions'], queryFn: () => listRecords<ClinicalCondition>('/hospital/clinical-conditions/') })
  const mappings = useQuery({ queryKey: ['specialty-mappings'], queryFn: () => listRecords<SpecialtyMapping>('/hospital/specialty-condition-mappings/') })

  const refresh = () => Promise.all([
    client.invalidateQueries({ queryKey: ['specialties'] }),
    client.invalidateQueries({ queryKey: ['conditions'] }),
    client.invalidateQueries({ queryKey: ['specialty-mappings'] }),
  ])
  const mutation = useMutation({
    mutationFn: async () => {
      if (dialog?.type === 'specialties') {
        const item = dialog.item as Specialty | undefined
        return item ? updateRecord('/hospital/specialties/', item.id, specialtyForm) : createRecord('/hospital/specialties/', specialtyForm)
      }
      if (dialog?.type === 'conditions') {
        const item = dialog.item as ClinicalCondition | undefined
        return item ? updateRecord('/hospital/clinical-conditions/', item.id, conditionForm) : createRecord('/hospital/clinical-conditions/', conditionForm)
      }
      const item = dialog?.item as SpecialtyMapping | undefined
      return item ? updateRecord('/hospital/specialty-condition-mappings/', item.id, mappingForm) : createRecord('/hospital/specialty-condition-mappings/', mappingForm)
    },
    onSuccess: async () => { setDialog(null); await refresh() },
  })

  const openNew = () => {
    mutation.reset()
    if (tab === 'specialties') setSpecialtyForm({ code: '', name: '', description: '', is_active: true })
    if (tab === 'conditions') setConditionForm({ coding_system: 'LOCAL', code: '', name: '', description: '', is_active: true })
    if (tab === 'mappings') setMappingForm({ specialty: specialties.data?.[0]?.id ?? '', condition: conditions.data?.[0]?.id ?? '', match_weight: '1.00', notes: '' })
    setDialog({ type: tab })
  }
  const openEdit = (type: Tab, item: Specialty | ClinicalCondition | SpecialtyMapping) => {
    mutation.reset()
    if (type === 'specialties') { const value = item as Specialty; setSpecialtyForm({ code: value.code, name: value.name, description: value.description, is_active: value.is_active }) }
    if (type === 'conditions') { const value = item as ClinicalCondition; setConditionForm({ coding_system: value.coding_system, code: value.code, name: value.name, description: value.description, is_active: value.is_active }) }
    if (type === 'mappings') { const value = item as SpecialtyMapping; setMappingForm({ specialty: value.specialty, condition: value.condition, match_weight: value.match_weight, notes: value.notes }) }
    setDialog({ type, item })
  }
  const loading = specialties.isPending || conditions.isPending || mappings.isPending
  const buttonLabel = tab === 'specialties' ? 'Add specialty' : tab === 'conditions' ? 'Add condition' : 'Map condition'

  return <div className="workspace-page">
    <PageHeader eyebrow="Clinical directory" title="Specialties and condition matching" description="Define the hospital vocabulary used for staff expertise and explainable transfer recommendations." actions={<Button onClick={openNew}><Plus size={16} /> {buttonLabel}</Button>} />
    <div className="tabs" role="tablist" aria-label="Clinical directory sections"><button className={tab === 'specialties' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('specialties')}><Stethoscope size={17} /> Specialties <span>{specialties.data?.length ?? 0}</span></button><button className={tab === 'conditions' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('conditions')}>Conditions <span>{conditions.data?.length ?? 0}</span></button><button className={tab === 'mappings' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('mappings')}><GitBranch size={17} /> Matching rules <span>{mappings.data?.length ?? 0}</span></button></div>
    <section className="section-panel table-panel">
      {loading ? <SectionLoader /> : tab === 'specialties' ? <>
        <div className="section-panel__heading"><div><p className="eyebrow">Specialist capabilities</p><h2>Specialties</h2></div></div>
        {(specialties.data?.length ?? 0) === 0 ? <EmptyState title="No specialties configured" description="Add specialties before assigning expertise or building transfer matches." action={<Button onClick={openNew}>Add specialty</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Specialty</th><th>Description</th><th>Condition mappings</th><th>Status</th><th /></tr></thead><tbody>{specialties.data!.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.code}</small></td><td>{item.description || 'No description'}</td><td>{item.condition_count}</td><td><StatusBadge status={item.is_active ? 'ACTIVE' : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => openEdit('specialties', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}
      </> : tab === 'conditions' ? <>
        <div className="section-panel__heading"><div><p className="eyebrow">Clinical vocabulary</p><h2>Conditions</h2></div></div>
        {(conditions.data?.length ?? 0) === 0 ? <EmptyState title="No conditions configured" description="Add hospital-approved condition labels; no diagnosis is generated from this directory." action={<Button onClick={openNew}>Add condition</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Condition</th><th>Code system</th><th>Description</th><th>Specialties</th><th>Status</th><th /></tr></thead><tbody>{conditions.data!.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.code}</small></td><td>{item.coding_system}</td><td>{item.description || 'No description'}</td><td>{item.specialty_count}</td><td><StatusBadge status={item.is_active ? 'ACTIVE' : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => openEdit('conditions', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}
      </> : <>
        <div className="section-panel__heading"><div><p className="eyebrow">Explainable matching</p><h2>Condition-to-specialty mappings</h2></div></div>
        {(mappings.data?.length ?? 0) === 0 ? <EmptyState title="No matching rules configured" description="Map conditions to the specialties that can address them. Weights remain visible and explainable." action={<Button onClick={openNew}>Map a condition</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Condition</th><th>Matched specialty</th><th>Weight</th><th>Notes</th><th /></tr></thead><tbody>{mappings.data!.map((item) => <tr key={item.id}><td><strong>{item.condition_name}</strong><small>{item.condition_code}</small></td><td>{item.specialty_name}</td><td>{item.match_weight}</td><td>{item.notes || '—'}</td><td><Button variant="ghost" onClick={() => openEdit('mappings', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}
      </>}
    </section>

    <Modal open={Boolean(dialog)} onClose={() => setDialog(null)} title={dialog?.item ? `Edit ${dialog.type === 'mappings' ? 'mapping' : dialog.type.slice(0, -1)}` : buttonLabel}>
      <form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        {dialog?.type === 'specialties' && <><div className="form-grid"><FormField label="Code" required value={specialtyForm.code} onChange={(e) => setSpecialtyForm({ ...specialtyForm, code: e.target.value.toUpperCase() })} /><FormField label="Name" required value={specialtyForm.name} onChange={(e) => setSpecialtyForm({ ...specialtyForm, name: e.target.value })} /></div><TextAreaField label="Description" rows={3} value={specialtyForm.description} onChange={(e) => setSpecialtyForm({ ...specialtyForm, description: e.target.value })} /><label className="check-field"><input type="checkbox" checked={specialtyForm.is_active} onChange={(e) => setSpecialtyForm({ ...specialtyForm, is_active: e.target.checked })} /><span><strong>Specialty is active</strong></span></label></>}
        {dialog?.type === 'conditions' && <><div className="form-grid"><FormField label="Coding system" required value={conditionForm.coding_system} onChange={(e) => setConditionForm({ ...conditionForm, coding_system: e.target.value.toUpperCase() })} /><FormField label="Code" required value={conditionForm.code} onChange={(e) => setConditionForm({ ...conditionForm, code: e.target.value })} /></div><FormField label="Condition name" required value={conditionForm.name} onChange={(e) => setConditionForm({ ...conditionForm, name: e.target.value })} /><TextAreaField label="Description" rows={3} value={conditionForm.description} onChange={(e) => setConditionForm({ ...conditionForm, description: e.target.value })} /><label className="check-field"><input type="checkbox" checked={conditionForm.is_active} onChange={(e) => setConditionForm({ ...conditionForm, is_active: e.target.checked })} /><span><strong>Condition is active</strong></span></label></>}
        {dialog?.type === 'mappings' && <><SelectField label="Condition" required value={mappingForm.condition} onChange={(e) => setMappingForm({ ...mappingForm, condition: e.target.value })}><option value="">Select condition</option>{conditions.data?.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.code}</option>)}</SelectField><SelectField label="Matched specialty" required value={mappingForm.specialty} onChange={(e) => setMappingForm({ ...mappingForm, specialty: e.target.value })}><option value="">Select specialty</option>{specialties.data?.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><FormField label="Match weight" required type="number" min="0.1" max="100" step="0.1" helperText="A visible relative weight used by the rule-based recommendation engine." value={mappingForm.match_weight} onChange={(e) => setMappingForm({ ...mappingForm, match_weight: e.target.value })} /><FormField label="Notes" value={mappingForm.notes} onChange={(e) => setMappingForm({ ...mappingForm, notes: e.target.value })} /></>}
        {mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Unable to save this record.'}</Alert>}
        <div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setDialog(null)}>Cancel</Button><Button type="submit" isLoading={mutation.isPending}>Save</Button></div>
      </form>
    </Modal>
  </div>
}
