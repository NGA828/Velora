import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clock3, Plus, Save, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { FormField } from '../../../shared/ui/forms/FormField'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getPatients } from '../../patient-care/shared/api'
import { createPrescription, getMedications } from '../../prescriptions/shared/api'

interface ItemForm { key: string; medication: string; dose_amount: string; dose_unit: string; route: string; frequency_display: string; duration_days: string; instructions: string; times: string[]; days: number[] }
const today = new Date().toISOString().slice(0, 10)
const endDefault = new Date(Date.now() + 6 * 86_400_000).toISOString().slice(0, 10)
const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const newItem = (medication = ''): ItemForm => ({ key: crypto.randomUUID(), medication, dose_amount: '1', dose_unit: 'tablet', route: 'ORAL', frequency_display: 'Once daily', duration_days: '7', instructions: '', times: ['08:00'], days: [] })
const itemPayload = (item: ItemForm) => ({
  medication: item.medication,
  dose_amount: item.dose_amount,
  dose_unit: item.dose_unit,
  route: item.route,
  frequency_display: item.frequency_display,
  duration_days: Number(item.duration_days),
  instructions: item.instructions,
  schedule_type: 'SCHEDULED',
  schedule_times: item.times.filter(Boolean).map((local_time) => ({ local_time, days_of_week: item.days })),
})

export function CreatePrescriptionPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const patients = useQuery({ queryKey: ['patients', 'doctor'], queryFn: () => getPatients() })
  const medications = useQuery({ queryKey: ['medications', 'active'], queryFn: () => getMedications(true) })
  const [patient, setPatient] = useState(params.get('patient') ?? '')
  const [startsOn, setStartsOn] = useState(today)
  const [endsOn, setEndsOn] = useState(endDefault)
  const [instructions, setInstructions] = useState('')
  const [items, setItems] = useState<ItemForm[]>([newItem()])
  const updateItem = (key: string, update: Partial<ItemForm>) => setItems((current) => current.map((item) => item.key === key ? { ...item, ...update } : item))
  const mutation = useMutation({
    mutationFn: () => createPrescription({ patient, starts_on: startsOn, ends_on: endsOn, clinical_instructions: instructions, items: items.map(itemPayload) }),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ['prescriptions'] }); navigate(patient ? `/doctor/patients/${patient}/prescriptions` : '/doctor/prescriptions', { replace: true }) },
  })
  const noSetup = (patients.data?.length ?? 0) === 0 || (medications.data?.length ?? 0) === 0
  return <div className="workspace-page workspace-page--narrow"><div className="back-link"><Link to="/doctor/prescriptions"><ArrowLeft size={16} /> Back to prescriptions</Link></div><PageHeader eyebrow="Medication order" title="Create prescription" description="Build a complete draft with explicit medication, dose, route, dates and scheduled times." />{noSetup && <Alert tone="critical" title="Configuration required">An assigned patient and at least one active medication catalogue entry are required.</Alert>}<form className="prescription-form" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}><section className="section-panel"><div className="form-section-heading"><span>1</span><div><h2>Patient and treatment period</h2><p>The prescription remains a draft until you explicitly activate it.</p></div></div><SelectField label="Patient" required value={patient} onChange={(e) => setPatient(e.target.value)}><option value="">Select assigned patient</option>{patients.data?.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.medical_record_number}</option>)}</SelectField><div className="form-grid"><FormField label="Start date" type="date" min={today} required value={startsOn} onChange={(e) => setStartsOn(e.target.value)} /><FormField label="End date" type="date" min={startsOn} required value={endsOn} onChange={(e) => setEndsOn(e.target.value)} /></div><TextAreaField label="Overall clinical instructions" rows={3} value={instructions} onChange={(e) => setInstructions(e.target.value)} /></section><section className="section-panel"><div className="section-panel__heading"><div><p className="eyebrow">Medication items</p><h2>Dosage and schedule</h2></div><Button type="button" variant="secondary" disabled={(medications.data?.length ?? 0) === 0} onClick={() => setItems([...items, newItem(medications.data?.[0]?.id)])}><Plus size={15} /> Add medication</Button></div><div className="prescription-items">{items.map((item, index) => <article key={item.key} className="prescription-item-form"><header><span>{index + 1}</span><strong>Medication item</strong>{items.length > 1 && <button type="button" onClick={() => setItems(items.filter((value) => value.key !== item.key))} aria-label="Remove medication"><Trash2 size={16} /></button>}</header><SelectField label="Medication" required value={item.medication} onChange={(e) => updateItem(item.key, { medication: e.target.value })}><option value="">Select medication</option>{medications.data?.map((medication) => <option key={medication.id} value={medication.id}>{medication.display_name}</option>)}</SelectField><div className="form-grid form-grid--three"><FormField label="Dose amount" type="number" min="0.001" step="0.001" required value={item.dose_amount} onChange={(e) => updateItem(item.key, { dose_amount: e.target.value })} /><FormField label="Dose unit" required value={item.dose_unit} onChange={(e) => updateItem(item.key, { dose_unit: e.target.value })} /><SelectField label="Route" value={item.route} onChange={(e) => updateItem(item.key, { route: e.target.value })}><option value="ORAL">Oral</option><option value="INTRAVENOUS">Intravenous</option><option value="INTRAMUSCULAR">Intramuscular</option><option value="SUBCUTANEOUS">Subcutaneous</option><option value="TOPICAL">Topical</option><option value="INHALATION">Inhalation</option><option value="OTHER">Other</option></SelectField></div><div className="form-grid"><FormField label="Frequency description" required value={item.frequency_display} onChange={(e) => updateItem(item.key, { frequency_display: e.target.value })} /><FormField label="Duration (days)" type="number" min="1" max="366" required value={item.duration_days} onChange={(e) => updateItem(item.key, { duration_days: e.target.value })} /></div><TextAreaField label="Medication instructions" rows={2} value={item.instructions} onChange={(e) => updateItem(item.key, { instructions: e.target.value })} /><fieldset className="schedule-fieldset"><legend><Clock3 size={15} /> Scheduled times</legend><div className="schedule-times">{item.times.map((doseTime, timeIndex) => <div key={`${item.key}-${timeIndex}`}><input type="time" required value={doseTime} onChange={(e) => updateItem(item.key, { times: item.times.map((value, valueIndex) => valueIndex === timeIndex ? e.target.value : value) })} />{item.times.length > 1 && <button type="button" onClick={() => updateItem(item.key, { times: item.times.filter((_, valueIndex) => valueIndex !== timeIndex) })}>Remove</button>}</div>)}</div><Button type="button" variant="ghost" onClick={() => updateItem(item.key, { times: [...item.times, '12:00'] })}><Plus size={14} /> Add time</Button><p>Leave all days unselected to schedule every day.</p><div className="weekday-picker">{dayLabels.map((label, day) => <label key={label}><input type="checkbox" checked={item.days.includes(day)} onChange={(e) => updateItem(item.key, { days: e.target.checked ? [...item.days, day].sort() : item.days.filter((value) => value !== day) })} /><span>{label}</span></label>)}</div></fieldset></article>)}</div></section>{mutation.error && <Alert tone="critical" title="Prescription was not created">{mutation.error instanceof AppApiError ? mutation.error.message : 'Review the prescription and try again.'}</Alert>}<div className="registration-submit"><div><Clock3 /><span><strong>Draft first</strong><small>Doses are generated only after Doctor activation.</small></span></div><Button type="submit" disabled={noSetup || !patient} isLoading={mutation.isPending}><Save size={17} /> Save prescription draft</Button></div></form></div>
}
