import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BedDouble, Boxes, Pencil, Plus, Wrench } from 'lucide-react'
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
import type { Bed, Department, Resource, Room, ServiceAvailability, ServiceDefinition } from '../shared/types'

type Tab = 'resources' | 'rooms' | 'services'
type DialogType = 'resource' | 'room' | 'bed' | 'service' | 'availability'
interface DialogState { type: DialogType; item?: Resource | Room | Bed | ServiceDefinition | ServiceAvailability }

const resourceBlank = { asset_code: '', name: '', category: 'EQUIPMENT', department: '', quantity_total: '1', quantity_available: '1', status: 'AVAILABLE', notes: '' }
const roomBlank = { code: '', department: '', floor: '', room_type: '', status: 'ACTIVE' }
const bedBlank = { code: '', room: '', status: 'AVAILABLE', notes: '' }
const serviceBlank = { code: '', name: '', category: '', description: '', is_active: true }
const availabilityBlank = { service: '', department: '', availability_status: 'AVAILABLE', notes: '' }

export function ResourcesPage() {
  const client = useQueryClient()
  const [tab, setTab] = useState<Tab>('resources')
  const [dialog, setDialog] = useState<DialogState | null>(null)
  const [resourceForm, setResourceForm] = useState(resourceBlank)
  const [roomForm, setRoomForm] = useState(roomBlank)
  const [bedForm, setBedForm] = useState(bedBlank)
  const [serviceForm, setServiceForm] = useState(serviceBlank)
  const [availabilityForm, setAvailabilityForm] = useState(availabilityBlank)
  const departments = useQuery({ queryKey: ['departments'], queryFn: () => listRecords<Department>('/hospital/departments/', { is_active: 'true' }) })
  const resources = useQuery({ queryKey: ['resources'], queryFn: () => listRecords<Resource>('/hospital/resources/') })
  const rooms = useQuery({ queryKey: ['rooms'], queryFn: () => listRecords<Room>('/hospital/rooms/') })
  const beds = useQuery({ queryKey: ['beds'], queryFn: () => listRecords<Bed>('/hospital/beds/') })
  const services = useQuery({ queryKey: ['services'], queryFn: () => listRecords<ServiceDefinition>('/hospital/services/') })
  const availability = useQuery({ queryKey: ['service-availability'], queryFn: () => listRecords<ServiceAvailability>('/hospital/service-availability/') })

  const refresh = () => Promise.all([
    client.invalidateQueries({ queryKey: ['resources'] }), client.invalidateQueries({ queryKey: ['rooms'] }), client.invalidateQueries({ queryKey: ['beds'] }),
    client.invalidateQueries({ queryKey: ['services'] }), client.invalidateQueries({ queryKey: ['service-availability'] }), client.invalidateQueries({ queryKey: ['head-of-service', 'dashboard'] }),
  ])
  const mutation = useMutation({
    mutationFn: async () => {
      if (!dialog) throw new Error('No configuration dialog selected.')
      const item = dialog.item
      if (dialog.type === 'resource') { const payload = { ...resourceForm, quantity_total: Number(resourceForm.quantity_total), quantity_available: Number(resourceForm.quantity_available) }; return item ? updateRecord('/hospital/resources/', item.id, payload) : createRecord('/hospital/resources/', payload) }
      if (dialog.type === 'room') return item ? updateRecord('/hospital/rooms/', item.id, roomForm) : createRecord('/hospital/rooms/', roomForm)
      if (dialog.type === 'bed') return item ? updateRecord('/hospital/beds/', item.id, bedForm) : createRecord('/hospital/beds/', bedForm)
      if (dialog.type === 'service') return item ? updateRecord('/hospital/services/', item.id, serviceForm) : createRecord('/hospital/services/', serviceForm)
      return item ? updateRecord('/hospital/service-availability/', item.id, availabilityForm) : createRecord('/hospital/service-availability/', availabilityForm)
    },
    onSuccess: async () => { setDialog(null); await refresh() },
  })

  const openNew = (type: DialogType) => {
    mutation.reset()
    if (type === 'resource') setResourceForm({ ...resourceBlank, department: departments.data?.[0]?.id ?? '' })
    if (type === 'room') setRoomForm({ ...roomBlank, department: departments.data?.[0]?.id ?? '' })
    if (type === 'bed') setBedForm({ ...bedBlank, room: rooms.data?.[0]?.id ?? '' })
    if (type === 'service') setServiceForm(serviceBlank)
    if (type === 'availability') setAvailabilityForm({ ...availabilityBlank, service: services.data?.[0]?.id ?? '', department: departments.data?.[0]?.id ?? '' })
    setDialog({ type })
  }
  const edit = (type: DialogType, item: DialogState['item']) => {
    mutation.reset()
    if (type === 'resource') { const x = item as Resource; setResourceForm({ asset_code: x.asset_code, name: x.name, category: x.category, department: x.department, quantity_total: String(x.quantity_total), quantity_available: String(x.quantity_available), status: x.status, notes: x.notes }) }
    if (type === 'room') { const x = item as Room; setRoomForm({ code: x.code, department: x.department, floor: x.floor, room_type: x.room_type, status: x.status }) }
    if (type === 'bed') { const x = item as Bed; setBedForm({ code: x.code, room: x.room, status: x.status, notes: x.notes }) }
    if (type === 'service') { const x = item as ServiceDefinition; setServiceForm({ code: x.code, name: x.name, category: x.category, description: x.description, is_active: x.is_active }) }
    if (type === 'availability') { const x = item as ServiceAvailability; setAvailabilityForm({ service: x.service, department: x.department, availability_status: x.availability_status, notes: x.notes }) }
    setDialog({ type, item })
  }
  const loading = resources.isPending || rooms.isPending || beds.isPending || services.isPending || availability.isPending

  return <div className="workspace-page">
    <PageHeader eyebrow="Hospital resources" title="Services, rooms, beds and equipment" description="Keep operational availability accurate so care teams can make informed decisions." actions={<Button onClick={() => openNew(tab === 'resources' ? 'resource' : tab === 'rooms' ? 'room' : 'service')}><Plus size={16} /> Add {tab === 'resources' ? 'resource' : tab === 'rooms' ? 'room' : 'service'}</Button>} />
    <div className="tabs" role="tablist"><button className={tab === 'resources' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('resources')}><Boxes size={17} /> Resources <span>{resources.data?.length ?? 0}</span></button><button className={tab === 'rooms' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('rooms')}><BedDouble size={17} /> Rooms & beds <span>{beds.data?.length ?? 0}</span></button><button className={tab === 'services' ? 'tabs__tab tabs__tab--active' : 'tabs__tab'} onClick={() => setTab('services')}><Wrench size={17} /> Services <span>{services.data?.length ?? 0}</span></button></div>
    {loading ? <section className="section-panel"><SectionLoader /></section> : tab === 'resources' ? <section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Equipment and supplies</p><h2>Resource availability</h2></div></div>{(resources.data?.length ?? 0) === 0 ? <EmptyState title="No resources recorded" description="Register equipment and supplies by department." action={<Button onClick={() => openNew('resource')}>Add resource</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Resource</th><th>Category</th><th>Department</th><th>Available</th><th>Status</th><th /></tr></thead><tbody>{resources.data!.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.asset_code}</small></td><td>{item.category.toLowerCase()}</td><td>{item.department_name}</td><td>{item.quantity_available} / {item.quantity_total}</td><td><StatusBadge status={item.status} /></td><td><Button variant="ghost" onClick={() => edit('resource', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}</section> : tab === 'rooms' ? <div className="stacked-panels"><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Facilities</p><h2>Rooms</h2></div><Button variant="secondary" onClick={() => openNew('room')}><Plus size={15} /> Add room</Button></div>{(rooms.data?.length ?? 0) === 0 ? <EmptyState title="No rooms configured" description="Add a room before registering beds." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Room</th><th>Department</th><th>Type</th><th>Beds available</th><th>Status</th><th /></tr></thead><tbody>{rooms.data!.map((item) => <tr key={item.id}><td><strong>{item.code}</strong><small>{item.floor || 'Floor not set'}</small></td><td>{item.department_name}</td><td>{item.room_type}</td><td>{item.available_bed_count} / {item.bed_count}</td><td><StatusBadge status={item.status} /></td><td><Button variant="ghost" onClick={() => edit('room', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}</section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Capacity</p><h2>Beds</h2></div><Button variant="secondary" disabled={(rooms.data?.length ?? 0) === 0} onClick={() => openNew('bed')}><Plus size={15} /> Add bed</Button></div>{(beds.data?.length ?? 0) === 0 ? <EmptyState title="No beds configured" description="Beds will appear here after they are assigned to rooms." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Bed</th><th>Room</th><th>Department</th><th>Status</th><th>Notes</th><th /></tr></thead><tbody>{beds.data!.map((item) => <tr key={item.id}><td><strong>{item.code}</strong></td><td>{item.room_code}</td><td>{item.department_name}</td><td><StatusBadge status={item.status} /></td><td>{item.notes || '—'}</td><td><Button variant="ghost" onClick={() => edit('bed', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}</section></div> : <div className="stacked-panels"><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Service catalog</p><h2>Hospital services</h2></div><Button variant="secondary" onClick={() => openNew('service')}><Plus size={15} /> Add service</Button></div>{(services.data?.length ?? 0) === 0 ? <EmptyState title="No services configured" description="Define the services offered by the hospital." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Service</th><th>Category</th><th>Departments</th><th>Status</th><th /></tr></thead><tbody>{services.data!.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.code}</small></td><td>{item.category || 'General'}</td><td>{item.department_count}</td><td><StatusBadge status={item.is_active ? 'ACTIVE' : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => edit('service', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}</section><section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Operational coverage</p><h2>Department availability</h2></div><Button variant="secondary" disabled={(services.data?.length ?? 0) === 0 || (departments.data?.length ?? 0) === 0} onClick={() => openNew('availability')}><Plus size={15} /> Set availability</Button></div>{(availability.data?.length ?? 0) === 0 ? <EmptyState title="No service coverage configured" description="Connect services to the departments that provide them." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Service</th><th>Department</th><th>Availability</th><th>Notes</th><th /></tr></thead><tbody>{availability.data!.map((item) => <tr key={item.id}><td><strong>{item.service_name}</strong></td><td>{item.department_name}</td><td><StatusBadge status={item.availability_status} /></td><td>{item.notes || '—'}</td><td><Button variant="ghost" onClick={() => edit('availability', item)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}</section></div>}

    <Modal open={Boolean(dialog)} onClose={() => setDialog(null)} title={`${dialog?.item ? 'Edit' : 'Add'} ${dialog?.type ?? 'record'}`}>
      <form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        {dialog?.type === 'resource' && <><div className="form-grid"><FormField label="Asset code" required value={resourceForm.asset_code} onChange={(e) => setResourceForm({ ...resourceForm, asset_code: e.target.value.toUpperCase() })} /><FormField label="Name" required value={resourceForm.name} onChange={(e) => setResourceForm({ ...resourceForm, name: e.target.value })} /></div><div className="form-grid"><SelectField label="Category" value={resourceForm.category} onChange={(e) => setResourceForm({ ...resourceForm, category: e.target.value })}><option value="EQUIPMENT">Equipment</option><option value="SUPPLY">Supply</option><option value="OTHER">Other</option></SelectField><SelectField label="Department" required value={resourceForm.department} onChange={(e) => setResourceForm({ ...resourceForm, department: e.target.value })}><option value="">Select department</option>{departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField></div><div className="form-grid"><FormField label="Total quantity" type="number" required min="1" value={resourceForm.quantity_total} onChange={(e) => setResourceForm({ ...resourceForm, quantity_total: e.target.value })} /><FormField label="Available quantity" type="number" required min="0" value={resourceForm.quantity_available} onChange={(e) => setResourceForm({ ...resourceForm, quantity_available: e.target.value })} /></div><SelectField label="Status" value={resourceForm.status} onChange={(e) => setResourceForm({ ...resourceForm, status: e.target.value })}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option><option value="MAINTENANCE">Maintenance</option></SelectField><TextAreaField label="Notes" rows={2} value={resourceForm.notes} onChange={(e) => setResourceForm({ ...resourceForm, notes: e.target.value })} /></>}
        {dialog?.type === 'room' && <><div className="form-grid"><FormField label="Room code" required value={roomForm.code} onChange={(e) => setRoomForm({ ...roomForm, code: e.target.value.toUpperCase() })} /><SelectField label="Department" required value={roomForm.department} onChange={(e) => setRoomForm({ ...roomForm, department: e.target.value })}><option value="">Select department</option>{departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField></div><div className="form-grid"><FormField label="Floor" value={roomForm.floor} onChange={(e) => setRoomForm({ ...roomForm, floor: e.target.value })} /><FormField label="Room type" required value={roomForm.room_type} onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })} /></div><SelectField label="Status" value={roomForm.status} onChange={(e) => setRoomForm({ ...roomForm, status: e.target.value })}><option value="ACTIVE">Active</option><option value="MAINTENANCE">Maintenance</option><option value="CLOSED">Closed</option></SelectField></>}
        {dialog?.type === 'bed' && <><div className="form-grid"><FormField label="Bed code" required value={bedForm.code} onChange={(e) => setBedForm({ ...bedForm, code: e.target.value.toUpperCase() })} /><SelectField label="Room" required value={bedForm.room} onChange={(e) => setBedForm({ ...bedForm, room: e.target.value })}><option value="">Select room</option>{rooms.data?.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.department_name}</option>)}</SelectField></div><SelectField label="Status" value={bedForm.status} onChange={(e) => setBedForm({ ...bedForm, status: e.target.value })}><option value="AVAILABLE">Available</option><option value="OCCUPIED">Occupied</option><option value="MAINTENANCE">Maintenance</option><option value="UNAVAILABLE">Unavailable</option></SelectField><FormField label="Notes" value={bedForm.notes} onChange={(e) => setBedForm({ ...bedForm, notes: e.target.value })} /></>}
        {dialog?.type === 'service' && <><div className="form-grid"><FormField label="Service code" required value={serviceForm.code} onChange={(e) => setServiceForm({ ...serviceForm, code: e.target.value.toUpperCase() })} /><FormField label="Service name" required value={serviceForm.name} onChange={(e) => setServiceForm({ ...serviceForm, name: e.target.value })} /></div><FormField label="Category" value={serviceForm.category} onChange={(e) => setServiceForm({ ...serviceForm, category: e.target.value })} /><TextAreaField label="Description" rows={3} value={serviceForm.description} onChange={(e) => setServiceForm({ ...serviceForm, description: e.target.value })} /><label className="check-field"><input type="checkbox" checked={serviceForm.is_active} onChange={(e) => setServiceForm({ ...serviceForm, is_active: e.target.checked })} /><span><strong>Service is active</strong></span></label></>}
        {dialog?.type === 'availability' && <><SelectField label="Service" required value={availabilityForm.service} onChange={(e) => setAvailabilityForm({ ...availabilityForm, service: e.target.value })}>{services.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><SelectField label="Department" required value={availabilityForm.department} onChange={(e) => setAvailabilityForm({ ...availabilityForm, department: e.target.value })}>{departments.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField><SelectField label="Availability" value={availabilityForm.availability_status} onChange={(e) => setAvailabilityForm({ ...availabilityForm, availability_status: e.target.value })}><option value="AVAILABLE">Available</option><option value="LIMITED">Limited</option><option value="UNAVAILABLE">Unavailable</option></SelectField><FormField label="Notes" value={availabilityForm.notes} onChange={(e) => setAvailabilityForm({ ...availabilityForm, notes: e.target.value })} /></>}
        {mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Unable to save record.'}</Alert>}
        <div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setDialog(null)}>Cancel</Button><Button type="submit" isLoading={mutation.isPending}>Save</Button></div>
      </form>
    </Modal>
  </div>
}
