import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, CheckCircle2, MapPin, Pencil, Plus, Stethoscope, Wrench } from 'lucide-react'
import { useEffect, useState } from 'react'

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
import type { ExternalHospital, ExternalService, ExternalSpecialist, ExternalSpecialty, ServiceDefinition, Specialty } from '../shared/types'

type CapabilityType = 'specialty' | 'service' | 'specialist'
interface CapabilityDialog { type: CapabilityType; item?: ExternalSpecialty | ExternalService | ExternalSpecialist }
const hospitalBlank = { name: '', address: '', city: '', region: '', country: 'CM', latitude: '', longitude: '', email: '', phone: '', transfer_email: '', notes: '', is_active: true }

export function ExternalHospitalsPage() {
  const client = useQueryClient()
  const [hospitalOpen, setHospitalOpen] = useState(false)
  const [editingHospital, setEditingHospital] = useState<ExternalHospital | null>(null)
  const [hospitalForm, setHospitalForm] = useState(hospitalBlank)
  const [selectedId, setSelectedId] = useState<string>('')
  const [capabilityDialog, setCapabilityDialog] = useState<CapabilityDialog | null>(null)
  const [capabilityForm, setCapabilityForm] = useState({ specialty: '', service: '', full_name: '', title: '', phone: '', email: '', availability_status: 'AVAILABLE', notes: '', is_active: true })
  const hospitals = useQuery({ queryKey: ['external-hospitals'], queryFn: () => listRecords<ExternalHospital>('/hospital/external-hospitals/') })
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: () => listRecords<Specialty>('/hospital/specialties/', { is_active: 'true' }) })
  const services = useQuery({ queryKey: ['services'], queryFn: () => listRecords<ServiceDefinition>('/hospital/services/', { is_active: 'true' }) })
  const hospitalSpecialties = useQuery({ queryKey: ['external-hospital-specialties', selectedId], enabled: Boolean(selectedId), queryFn: () => listRecords<ExternalSpecialty>('/hospital/external-hospital-specialties/', { external_hospital: selectedId }) })
  const hospitalServices = useQuery({ queryKey: ['external-hospital-services', selectedId], enabled: Boolean(selectedId), queryFn: () => listRecords<ExternalService>('/hospital/external-hospital-services/', { external_hospital: selectedId }) })
  const specialists = useQuery({ queryKey: ['external-specialists', selectedId], enabled: Boolean(selectedId), queryFn: () => listRecords<ExternalSpecialist>('/hospital/external-specialists/', { external_hospital: selectedId }) })

  useEffect(() => {
    if (!selectedId && hospitals.data?.[0]) setSelectedId(hospitals.data[0].id)
    if (selectedId && hospitals.data && !hospitals.data.some((item) => item.id === selectedId)) setSelectedId(hospitals.data[0]?.id ?? '')
  }, [hospitals.data, selectedId])
  const selected = hospitals.data?.find((item) => item.id === selectedId)
  const refresh = () => Promise.all([
    client.invalidateQueries({ queryKey: ['external-hospitals'] }),
    client.invalidateQueries({ queryKey: ['external-hospital-specialties', selectedId] }),
    client.invalidateQueries({ queryKey: ['external-hospital-services', selectedId] }),
    client.invalidateQueries({ queryKey: ['external-specialists', selectedId] }),
    client.invalidateQueries({ queryKey: ['head-of-service', 'dashboard'] }),
  ])
  const hospitalMutation = useMutation({
    mutationFn: () => {
      const payload = { ...hospitalForm, latitude: hospitalForm.latitude || null, longitude: hospitalForm.longitude || null }
      return editingHospital ? updateRecord<ExternalHospital>('/hospital/external-hospitals/', editingHospital.id, payload) : createRecord<ExternalHospital>('/hospital/external-hospitals/', payload)
    },
    onSuccess: async (saved) => { setHospitalOpen(false); setEditingHospital(null); setSelectedId(saved.id); await refresh() },
  })
  const capabilityMutation = useMutation({
    mutationFn: () => {
      if (!capabilityDialog) throw new Error('No capability selected.')
      const item = capabilityDialog.item
      if (capabilityDialog.type === 'specialty') {
        const payload = { external_hospital: selectedId, specialty: capabilityForm.specialty, availability_status: capabilityForm.availability_status, notes: capabilityForm.notes }
        return item ? updateRecord('/hospital/external-hospital-specialties/', item.id, payload) : createRecord('/hospital/external-hospital-specialties/', payload)
      }
      if (capabilityDialog.type === 'service') {
        const payload = { external_hospital: selectedId, service: capabilityForm.service, availability_status: capabilityForm.availability_status, notes: capabilityForm.notes }
        return item ? updateRecord('/hospital/external-hospital-services/', item.id, payload) : createRecord('/hospital/external-hospital-services/', payload)
      }
      const payload = { external_hospital: selectedId, specialty: capabilityForm.specialty, full_name: capabilityForm.full_name, title: capabilityForm.title, phone: capabilityForm.phone, email: capabilityForm.email, is_active: capabilityForm.is_active }
      return item ? updateRecord('/hospital/external-specialists/', item.id, payload) : createRecord('/hospital/external-specialists/', payload)
    },
    onSuccess: async () => { setCapabilityDialog(null); await refresh() },
  })

  const openHospital = (item?: ExternalHospital) => {
    hospitalMutation.reset(); setEditingHospital(item ?? null)
    setHospitalForm(item ? { name: item.name, address: item.address, city: item.city, region: item.region, country: item.country, latitude: item.latitude ?? '', longitude: item.longitude ?? '', email: item.email, phone: item.phone, transfer_email: item.transfer_email, notes: item.notes, is_active: item.is_active } : hospitalBlank)
    setHospitalOpen(true)
  }
  const openCapability = (type: CapabilityType, item?: ExternalSpecialty | ExternalService | ExternalSpecialist) => {
    capabilityMutation.reset()
    if (type === 'specialty') { const x = item as ExternalSpecialty | undefined; setCapabilityForm({ specialty: x?.specialty ?? specialties.data?.[0]?.id ?? '', service: '', full_name: '', title: '', phone: '', email: '', availability_status: x?.availability_status ?? 'AVAILABLE', notes: x?.notes ?? '', is_active: true }) }
    if (type === 'service') { const x = item as ExternalService | undefined; setCapabilityForm({ specialty: '', service: x?.service ?? services.data?.[0]?.id ?? '', full_name: '', title: '', phone: '', email: '', availability_status: x?.availability_status ?? 'AVAILABLE', notes: x?.notes ?? '', is_active: true }) }
    if (type === 'specialist') { const x = item as ExternalSpecialist | undefined; setCapabilityForm({ specialty: x?.specialty ?? specialties.data?.[0]?.id ?? '', service: '', full_name: x?.full_name ?? '', title: x?.title ?? '', phone: x?.phone ?? '', email: x?.email ?? '', availability_status: 'AVAILABLE', notes: '', is_active: x?.is_active ?? true }) }
    setCapabilityDialog({ type, item })
  }

  return <div className="workspace-page">
    <PageHeader eyebrow="Transfer directory" title="External hospitals" description="Maintain the verified destinations, contacts and capabilities used by the recommendation engine." actions={<Button onClick={() => openHospital()}><Plus size={16} /> Add hospital</Button>} />
    {hospitals.isPending ? <SectionLoader /> : (hospitals.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No external hospitals registered" description="Add trusted receiving hospitals before Doctors initiate transfer recommendations." action={<Button onClick={() => openHospital()}>Add external hospital</Button>} /></section> : <div className="directory-layout">
      <aside className="directory-list" aria-label="External hospital list">{hospitals.data!.map((item) => <button key={item.id} className={item.id === selectedId ? 'directory-list__item directory-list__item--active' : 'directory-list__item'} onClick={() => setSelectedId(item.id)}><span className="directory-list__icon"><Building2 /></span><span><strong>{item.name}</strong><small><MapPin size={12} /> {item.city}, {item.country}</small></span>{item.transfer_ready ? <CheckCircle2 className="directory-list__ready" aria-label="Transfer ready" /> : <span className="directory-list__dot" aria-label="Profile incomplete" />}</button>)}</aside>
      {selected && <div className="directory-detail">
        <section className="section-panel external-summary"><div><p className="eyebrow">Selected hospital</p><h2>{selected.name}</h2><p>{selected.address}, {selected.city}{selected.region ? `, ${selected.region}` : ''}</p></div><div className="external-summary__actions"><StatusBadge status={selected.transfer_ready ? 'ACTIVE' : 'PENDING'} label={selected.transfer_ready ? 'Transfer ready' : 'Profile incomplete'} /><Button variant="secondary" onClick={() => openHospital(selected)}><Pencil size={15} /> Edit hospital</Button></div><dl><div><dt>Transfer email</dt><dd>{selected.transfer_email || 'Not provided'}</dd></div><div><dt>Telephone</dt><dd>{selected.phone}</dd></div><div><dt>General email</dt><dd>{selected.email || 'Not provided'}</dd></div></dl></section>
        <section className="section-panel capability-panel"><div className="section-panel__heading"><div><p className="eyebrow">Clinical capabilities</p><h2>Specialties</h2></div><Button variant="ghost" onClick={() => openCapability('specialty')} disabled={(specialties.data?.length ?? 0) === 0}><Plus size={15} /> Add</Button></div>{(hospitalSpecialties.data?.length ?? 0) === 0 ? <p className="inline-empty">No specialties recorded.</p> : <ul className="record-list">{hospitalSpecialties.data!.map((item) => <li key={item.id}><Stethoscope /><span><strong>{item.specialty_name}</strong><small>{item.notes || 'No notes'}</small></span><StatusBadge status={item.availability_status} /><Button variant="ghost" onClick={() => openCapability('specialty', item)}>Edit</Button></li>)}</ul>}</section>
        <section className="section-panel capability-panel"><div className="section-panel__heading"><div><p className="eyebrow">Operational capabilities</p><h2>Services</h2></div><Button variant="ghost" onClick={() => openCapability('service')} disabled={(services.data?.length ?? 0) === 0}><Plus size={15} /> Add</Button></div>{(hospitalServices.data?.length ?? 0) === 0 ? <p className="inline-empty">No services recorded.</p> : <ul className="record-list">{hospitalServices.data!.map((item) => <li key={item.id}><Wrench /><span><strong>{item.service_name}</strong><small>{item.notes || 'No notes'}</small></span><StatusBadge status={item.availability_status} /><Button variant="ghost" onClick={() => openCapability('service', item)}>Edit</Button></li>)}</ul>}</section>
        <section className="section-panel capability-panel"><div className="section-panel__heading"><div><p className="eyebrow">Contacts</p><h2>Available specialists</h2></div><Button variant="ghost" onClick={() => openCapability('specialist')} disabled={(specialties.data?.length ?? 0) === 0}><Plus size={15} /> Add</Button></div>{(specialists.data?.length ?? 0) === 0 ? <p className="inline-empty">No specialists recorded.</p> : <ul className="record-list">{specialists.data!.map((item) => <li key={item.id}><Stethoscope /><span><strong>{item.full_name}</strong><small>{item.specialty_name} · {item.email || item.phone || 'No direct contact'}</small></span><StatusBadge status={item.is_active ? 'ACTIVE' : 'INACTIVE'} /><Button variant="ghost" onClick={() => openCapability('specialist', item)}>Edit</Button></li>)}</ul>}</section>
      </div>}
    </div>}

    <Modal open={hospitalOpen} width="wide" onClose={() => setHospitalOpen(false)} title={editingHospital ? 'Edit external hospital' : 'Add external hospital'} description="Use verified contact information. Transfer readiness requires an email and at least one capability.">
      <form onSubmit={(event) => { event.preventDefault(); hospitalMutation.mutate() }}><FormField label="Hospital name" required value={hospitalForm.name} onChange={(e) => setHospitalForm({ ...hospitalForm, name: e.target.value })} /><TextAreaField label="Address" required rows={2} value={hospitalForm.address} onChange={(e) => setHospitalForm({ ...hospitalForm, address: e.target.value })} /><div className="form-grid form-grid--three"><FormField label="City" required value={hospitalForm.city} onChange={(e) => setHospitalForm({ ...hospitalForm, city: e.target.value })} /><FormField label="Region" value={hospitalForm.region} onChange={(e) => setHospitalForm({ ...hospitalForm, region: e.target.value })} /><FormField label="Country" required maxLength={2} value={hospitalForm.country} onChange={(e) => setHospitalForm({ ...hospitalForm, country: e.target.value.toUpperCase() })} /></div><div className="form-grid"><FormField label="Telephone" required value={hospitalForm.phone} onChange={(e) => setHospitalForm({ ...hospitalForm, phone: e.target.value })} /><FormField label="General email" type="email" value={hospitalForm.email} onChange={(e) => setHospitalForm({ ...hospitalForm, email: e.target.value })} /></div><FormField label="Medical transfer email" type="email" helperText="Approved medical packages will be sent to this address." value={hospitalForm.transfer_email} onChange={(e) => setHospitalForm({ ...hospitalForm, transfer_email: e.target.value })} /><div className="form-grid"><FormField label="Latitude (optional)" type="number" step="0.000001" min="-90" max="90" value={hospitalForm.latitude} onChange={(e) => setHospitalForm({ ...hospitalForm, latitude: e.target.value })} /><FormField label="Longitude (optional)" type="number" step="0.000001" min="-180" max="180" value={hospitalForm.longitude} onChange={(e) => setHospitalForm({ ...hospitalForm, longitude: e.target.value })} /></div><TextAreaField label="Transfer notes" rows={3} value={hospitalForm.notes} onChange={(e) => setHospitalForm({ ...hospitalForm, notes: e.target.value })} /><label className="check-field"><input type="checkbox" checked={hospitalForm.is_active} onChange={(e) => setHospitalForm({ ...hospitalForm, is_active: e.target.checked })} /><span><strong>Hospital is active in transfer directory</strong></span></label>{hospitalMutation.error && <Alert tone="critical">{hospitalMutation.error instanceof AppApiError ? hospitalMutation.error.message : 'Unable to save hospital.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setHospitalOpen(false)}>Cancel</Button><Button type="submit" isLoading={hospitalMutation.isPending}>Save hospital</Button></div></form>
    </Modal>

    <Modal open={Boolean(capabilityDialog)} onClose={() => setCapabilityDialog(null)} title={`${capabilityDialog?.item ? 'Edit' : 'Add'} ${capabilityDialog?.type ?? 'capability'}`}>
      <form onSubmit={(event) => { event.preventDefault(); capabilityMutation.mutate() }}>
        {capabilityDialog?.type === 'specialty' && <><SelectField label="Specialty" required value={capabilityForm.specialty} onChange={(e) => setCapabilityForm({ ...capabilityForm, specialty: e.target.value })}>{specialties.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><SelectField label="Availability" value={capabilityForm.availability_status} onChange={(e) => setCapabilityForm({ ...capabilityForm, availability_status: e.target.value })}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></SelectField><FormField label="Notes" value={capabilityForm.notes} onChange={(e) => setCapabilityForm({ ...capabilityForm, notes: e.target.value })} /></>}
        {capabilityDialog?.type === 'service' && <><SelectField label="Service" required value={capabilityForm.service} onChange={(e) => setCapabilityForm({ ...capabilityForm, service: e.target.value })}>{services.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><SelectField label="Availability" value={capabilityForm.availability_status} onChange={(e) => setCapabilityForm({ ...capabilityForm, availability_status: e.target.value })}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></SelectField><FormField label="Notes" value={capabilityForm.notes} onChange={(e) => setCapabilityForm({ ...capabilityForm, notes: e.target.value })} /></>}
        {capabilityDialog?.type === 'specialist' && <><FormField label="Full name" required value={capabilityForm.full_name} onChange={(e) => setCapabilityForm({ ...capabilityForm, full_name: e.target.value })} /><SelectField label="Specialty" required value={capabilityForm.specialty} onChange={(e) => setCapabilityForm({ ...capabilityForm, specialty: e.target.value })}>{specialties.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><FormField label="Title" value={capabilityForm.title} onChange={(e) => setCapabilityForm({ ...capabilityForm, title: e.target.value })} /><div className="form-grid"><FormField label="Telephone" value={capabilityForm.phone} onChange={(e) => setCapabilityForm({ ...capabilityForm, phone: e.target.value })} /><FormField label="Email" type="email" value={capabilityForm.email} onChange={(e) => setCapabilityForm({ ...capabilityForm, email: e.target.value })} /></div><label className="check-field"><input type="checkbox" checked={capabilityForm.is_active} onChange={(e) => setCapabilityForm({ ...capabilityForm, is_active: e.target.checked })} /><span><strong>Specialist is currently available</strong></span></label></>}
        {capabilityMutation.error && <Alert tone="critical">{capabilityMutation.error instanceof AppApiError ? capabilityMutation.error.message : 'Unable to save capability.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setCapabilityDialog(null)}>Cancel</Button><Button type="submit" isLoading={capabilityMutation.isPending}>Save</Button></div>
      </form>
    </Modal>
  </div>
}
