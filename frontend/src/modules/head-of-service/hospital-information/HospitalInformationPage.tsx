import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Save } from 'lucide-react'
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
import { createRecord, getRecord, listRecords, putRecord, updateRecord } from '../shared/api'
import type { Department, HospitalProfile } from '../shared/types'

const emptyProfile = { legal_name: '', display_name: '', registration_number: '', address: '', city: '', region: '', country: 'CM', email: '', phone: '', website: '', timezone: 'Africa/Lagos', billing_currency: 'XAF' }
const emptyDepartment = { code: '', name: '', description: '', location: '', phone: '', parent: '', is_active: true }

export function HospitalInformationPage() {
  const client = useQueryClient()
  const [profile, setProfile] = useState(emptyProfile)
  const [departmentOpen, setDepartmentOpen] = useState(false)
  const [editing, setEditing] = useState<Department | null>(null)
  const [departmentForm, setDepartmentForm] = useState(emptyDepartment)
  const profileQuery = useQuery({ queryKey: ['hospital-profile'], queryFn: () => getRecord<{ data: HospitalProfile | null }>('/hospital/profile/') })
  const departmentQuery = useQuery({ queryKey: ['departments'], queryFn: () => listRecords<Department>('/hospital/departments/') })

  useEffect(() => {
    if (profileQuery.data?.data) {
      const stored = profileQuery.data.data
      setProfile({
        legal_name: stored.legal_name,
        display_name: stored.display_name,
        registration_number: stored.registration_number,
        address: stored.address,
        city: stored.city,
        region: stored.region,
        country: stored.country,
        email: stored.email,
        phone: stored.phone,
        website: stored.website,
        timezone: stored.timezone,
        billing_currency: stored.billing_currency,
      })
    }
  }, [profileQuery.data])

  const profileMutation = useMutation({
    mutationFn: () => putRecord<{ data: HospitalProfile }>('/hospital/profile/', profile),
    onSuccess: async () => {
      await Promise.all([client.invalidateQueries({ queryKey: ['hospital-profile'] }), client.invalidateQueries({ queryKey: ['head-of-service', 'dashboard'] })])
    },
  })
  const departmentMutation = useMutation({
    mutationFn: () => editing
      ? updateRecord<Department>('/hospital/departments/', editing.id, { ...departmentForm, parent: departmentForm.parent || null })
      : createRecord<Department>('/hospital/departments/', { ...departmentForm, parent: departmentForm.parent || null }),
    onSuccess: async () => {
      setDepartmentOpen(false); setEditing(null); setDepartmentForm(emptyDepartment)
      await Promise.all([client.invalidateQueries({ queryKey: ['departments'] }), client.invalidateQueries({ queryKey: ['head-of-service', 'dashboard'] })])
    },
  })
  const openNew = () => { setEditing(null); setDepartmentForm(emptyDepartment); setDepartmentOpen(true) }
  const openEdit = (department: Department) => {
    setEditing(department)
    setDepartmentForm({ code: department.code, name: department.name, description: department.description, location: department.location, phone: department.phone, parent: department.parent ?? '', is_active: department.is_active })
    setDepartmentOpen(true)
  }

  return <div className="workspace-page">
    <PageHeader eyebrow="Hospital information" title="Hospital identity and departments" description="Maintain the trusted operational record used across staffing, care and transfers." />
    <section className="section-panel configuration-form-panel">
      <div className="section-panel__heading"><div><p className="eyebrow">Hospital profile</p><h2>Official contact and location</h2></div>{profileQuery.data?.data ? <StatusBadge status="ACTIVE" label="Configured" /> : <StatusBadge status="PENDING" label="Needs setup" />}</div>
      {profileQuery.isPending ? <SectionLoader /> : <form className="configuration-form" onSubmit={(event) => { event.preventDefault(); profileMutation.mutate() }}>
        <div className="form-grid"><FormField label="Display name" required value={profile.display_name} onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} /><FormField label="Legal name" required value={profile.legal_name} onChange={(e) => setProfile({ ...profile, legal_name: e.target.value })} /></div>
        <div className="form-grid"><FormField label="Registration number" value={profile.registration_number} onChange={(e) => setProfile({ ...profile, registration_number: e.target.value })} /><FormField label="Hospital timezone" required value={profile.timezone} onChange={(e) => setProfile({ ...profile, timezone: e.target.value })} /></div>
        <FormField label="Billing currency" required maxLength={3} helperText="Three-letter ISO 4217 code, stored on every new invoice." value={profile.billing_currency} onChange={(e) => setProfile({ ...profile, billing_currency: e.target.value.toUpperCase() })} />
        <TextAreaField label="Address" required rows={2} value={profile.address} onChange={(e) => setProfile({ ...profile, address: e.target.value })} />
        <div className="form-grid form-grid--three"><FormField label="City" required value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} /><FormField label="Region" value={profile.region} onChange={(e) => setProfile({ ...profile, region: e.target.value })} /><FormField label="Country code" required maxLength={2} value={profile.country} onChange={(e) => setProfile({ ...profile, country: e.target.value.toUpperCase() })} /></div>
        <div className="form-grid"><FormField label="Hospital email" required type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /><FormField label="Telephone" required value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} /></div>
        <FormField label="Website (optional)" type="url" value={profile.website} onChange={(e) => setProfile({ ...profile, website: e.target.value })} />
        {profileMutation.error && <Alert tone="critical">{profileMutation.error instanceof AppApiError ? profileMutation.error.message : 'Unable to save the hospital profile.'}</Alert>}
        {profileMutation.isSuccess && <Alert tone="success">Hospital profile saved.</Alert>}
        <div className="form-actions"><Button type="submit" isLoading={profileMutation.isPending}><Save size={17} /> Save hospital profile</Button></div>
      </form>}
    </section>

    <section className="section-panel table-panel">
      <div className="section-panel__heading"><div><p className="eyebrow">Structure</p><h2>Departments</h2></div><Button variant="secondary" onClick={openNew}><Plus size={16} /> Add department</Button></div>
      {departmentQuery.isPending ? <SectionLoader /> : (departmentQuery.data?.length ?? 0) === 0 ? <EmptyState title="No departments configured" description="Add the operational departments that staff, rooms and services belong to." action={<Button onClick={openNew}>Add department</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Department</th><th>Location</th><th>Parent</th><th>Personnel</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{departmentQuery.data!.map((department) => <tr key={department.id}><td><strong>{department.name}</strong><small>{department.code}</small></td><td>{department.location || 'Not specified'}</td><td>{department.parent_name || 'Top level'}</td><td>{department.staff_count}</td><td><StatusBadge status={department.is_active ? 'ACTIVE' : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => openEdit(department)}><Pencil size={15} /> Edit</Button></td></tr>)}</tbody></table></div>}
    </section>

    <Modal open={departmentOpen} onClose={() => setDepartmentOpen(false)} title={editing ? 'Edit department' : 'Add department'} description="Departments connect staff, rooms, resources and services.">
      <form onSubmit={(event) => { event.preventDefault(); departmentMutation.mutate() }}>
        <div className="form-grid"><FormField label="Code" required value={departmentForm.code} onChange={(e) => setDepartmentForm({ ...departmentForm, code: e.target.value.toUpperCase() })} /><FormField label="Name" required value={departmentForm.name} onChange={(e) => setDepartmentForm({ ...departmentForm, name: e.target.value })} /></div>
        <TextAreaField label="Description" rows={3} value={departmentForm.description} onChange={(e) => setDepartmentForm({ ...departmentForm, description: e.target.value })} />
        <div className="form-grid"><FormField label="Location" value={departmentForm.location} onChange={(e) => setDepartmentForm({ ...departmentForm, location: e.target.value })} /><FormField label="Telephone" value={departmentForm.phone} onChange={(e) => setDepartmentForm({ ...departmentForm, phone: e.target.value })} /></div>
        <SelectField label="Parent department" value={departmentForm.parent} onChange={(e) => setDepartmentForm({ ...departmentForm, parent: e.target.value })}><option value="">None</option>{departmentQuery.data?.filter((item) => item.id !== editing?.id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</SelectField>
        <label className="check-field"><input type="checkbox" checked={departmentForm.is_active} onChange={(e) => setDepartmentForm({ ...departmentForm, is_active: e.target.checked })} /><span><strong>Department is active</strong><small>Inactive departments remain in historical records.</small></span></label>
        {departmentMutation.error && <Alert tone="critical">{departmentMutation.error instanceof AppApiError ? departmentMutation.error.message : 'Unable to save department.'}</Alert>}
        <div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setDepartmentOpen(false)}>Cancel</Button><Button type="submit" isLoading={departmentMutation.isPending}>{editing ? 'Save changes' : 'Add department'}</Button></div>
      </form>
    </Modal>
  </div>
}
