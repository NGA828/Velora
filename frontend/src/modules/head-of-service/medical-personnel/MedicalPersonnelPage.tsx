import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MailPlus, Pencil, RotateCcw, UserRoundPlus, UsersRound } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { FormField } from '../../../shared/ui/forms/FormField'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { createRecord, listRecords, postAction, updateRecord } from '../shared/api'
import type { Department, Invitation, Staff } from '../shared/types'

const emptyInvite = { email: '', intended_role: 'DOCTOR', employee_number: '', department_id: '', job_title: '', license_number: '', hire_date: '' }

export function MedicalPersonnelPage() {
  const client = useQueryClient()
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteForm, setInviteForm] = useState(emptyInvite)
  const [editing, setEditing] = useState<Staff | null>(null)
  const [staffForm, setStaffForm] = useState({ department: '', job_title: '', license_number: '', employment_status: 'ACTIVE', account_active: true })
  const staffQuery = useQuery({ queryKey: ['staff'], queryFn: () => listRecords<Staff>('/staff/') })
  const invitationQuery = useQuery({ queryKey: ['staff-invitations'], queryFn: () => listRecords<Invitation>('/staff/invitations/') })
  const departmentQuery = useQuery({ queryKey: ['departments'], queryFn: () => listRecords<Department>('/hospital/departments/', { is_active: 'true' }) })

  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['staff'] }),
      client.invalidateQueries({ queryKey: ['staff-invitations'] }),
      client.invalidateQueries({ queryKey: ['head-of-service', 'dashboard'] }),
    ])
  }
  const inviteMutation = useMutation({
    mutationFn: () => createRecord<Invitation>('/staff/invitations/', { ...inviteForm, department_id: inviteForm.department_id || null, hire_date: inviteForm.hire_date || null }),
    onSuccess: async () => { setInviteOpen(false); setInviteForm(emptyInvite); await refresh() },
  })
  const updateMutation = useMutation({
    mutationFn: () => updateRecord<Staff>('/staff/', editing!.id, { ...staffForm, department: staffForm.department || null }),
    onSuccess: async () => { setEditing(null); await refresh() },
  })
  const revokeMutation = useMutation({
    mutationFn: (id: string) => postAction<Invitation>(`/staff/invitations/${id}/revoke/`),
    onSuccess: refresh,
  })

  const openStaff = (staff: Staff) => {
    setEditing(staff)
    setStaffForm({ department: staff.department ?? '', job_title: staff.job_title, license_number: staff.license_number, employment_status: staff.employment_status, account_active: staff.account_active })
  }
  const pendingInvitations = (invitationQuery.data ?? []).filter((item) => item.status === 'PENDING')
  const error = inviteMutation.error ?? updateMutation.error ?? revokeMutation.error

  return <div className="workspace-page">
    <PageHeader eyebrow="Medical personnel" title="Staff access and assignments" description="Invite Doctors and Nurses, then maintain their operational status and department." actions={<Button onClick={() => setInviteOpen(true)}><UserRoundPlus size={17} /> Invite staff</Button>} />
    {error && <Alert tone="critical" title="Action not completed">{error instanceof AppApiError ? error.message : 'Please try again.'}</Alert>}
    <section className="summary-strip"><div><UsersRound /><span><small>Active accounts</small><strong>{(staffQuery.data ?? []).filter((item) => item.account_active).length}</strong></span></div><div><MailPlus /><span><small>Pending invitations</small><strong>{pendingInvitations.length}</strong></span></div><div><RotateCcw /><span><small>On leave</small><strong>{(staffQuery.data ?? []).filter((item) => item.employment_status === 'ON_LEAVE').length}</strong></span></div></section>

    <section className="section-panel table-panel">
      <div className="section-panel__heading"><div><p className="eyebrow">Directory</p><h2>Doctors and Nurses</h2></div><span>{staffQuery.data?.length ?? 0} people</span></div>
      {staffQuery.isPending ? <SectionLoader /> : (staffQuery.data?.length ?? 0) === 0 ? <EmptyState title="No medical personnel yet" description="Invite the first Doctor or Nurse to begin the care-team directory." action={<Button onClick={() => setInviteOpen(true)}>Invite staff</Button>} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Person</th><th>Role</th><th>Department</th><th>Employee no.</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{staffQuery.data!.map((staff) => <tr key={staff.id}><td><strong>{staff.full_name}</strong><small>{staff.email}</small></td><td>{staff.role_label}<small>{staff.job_title || 'No title set'}</small></td><td>{staff.department_name || 'Unassigned'}</td><td>{staff.employee_number}</td><td><StatusBadge status={staff.account_active ? staff.employment_status : 'INACTIVE'} /></td><td><Button variant="ghost" onClick={() => openStaff(staff)}><Pencil size={15} /> Manage</Button></td></tr>)}</tbody></table></div>}
    </section>

    <section className="section-panel table-panel">
      <div className="section-panel__heading"><div><p className="eyebrow">Onboarding</p><h2>Invitation history</h2></div><span>{invitationQuery.data?.length ?? 0} invitations</span></div>
      {invitationQuery.isPending ? <SectionLoader /> : (invitationQuery.data?.length ?? 0) === 0 ? <EmptyState title="No invitations sent" description="Staff invitations and their acceptance status will appear here." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Email</th><th>Role</th><th>Sent by</th><th>Expires</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{invitationQuery.data!.map((invitation) => <tr key={invitation.id}><td><strong>{invitation.email}</strong></td><td>{invitation.intended_role_label}</td><td>{invitation.invited_by_name}</td><td>{new Date(invitation.expires_at).toLocaleDateString()}</td><td><StatusBadge status={invitation.status} /></td><td>{invitation.status === 'PENDING' && <Button variant="ghost" onClick={() => revokeMutation.mutate(invitation.id)} disabled={revokeMutation.isPending}>Revoke</Button>}</td></tr>)}</tbody></table></div>}
    </section>

    <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Invite medical personnel" description="The recipient will set their own password through an expiring email link.">
      <form onSubmit={(event) => { event.preventDefault(); inviteMutation.mutate() }}>
        <FormField label="Work email" type="email" required value={inviteForm.email} onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} />
        <div className="form-grid"><SelectField label="Role" value={inviteForm.intended_role} onChange={(e) => setInviteForm({ ...inviteForm, intended_role: e.target.value })}><option value="DOCTOR">Doctor</option><option value="NURSE">Nurse</option></SelectField><FormField label="Employee number" required value={inviteForm.employee_number} onChange={(e) => setInviteForm({ ...inviteForm, employee_number: e.target.value })} /></div>
        <SelectField label="Department" value={inviteForm.department_id} onChange={(e) => setInviteForm({ ...inviteForm, department_id: e.target.value })}><option value="">Not assigned yet</option>{departmentQuery.data?.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</SelectField>
        <div className="form-grid"><FormField label="Job title" value={inviteForm.job_title} onChange={(e) => setInviteForm({ ...inviteForm, job_title: e.target.value })} /><FormField label="License number" value={inviteForm.license_number} onChange={(e) => setInviteForm({ ...inviteForm, license_number: e.target.value })} /></div>
        <FormField label="Hire date" type="date" value={inviteForm.hire_date} onChange={(e) => setInviteForm({ ...inviteForm, hire_date: e.target.value })} />
        {inviteMutation.error && <Alert tone="critical">{inviteMutation.error instanceof AppApiError ? inviteMutation.error.message : 'Unable to send invitation.'}</Alert>}
        <div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setInviteOpen(false)}>Cancel</Button><Button type="submit" isLoading={inviteMutation.isPending}>Send secure invitation</Button></div>
      </form>
    </Modal>

    <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title="Manage staff member" description={editing ? `${editing.full_name} · ${editing.employee_number}` : undefined}>
      <form onSubmit={(event) => { event.preventDefault(); updateMutation.mutate() }}>
        <SelectField label="Department" value={staffForm.department} onChange={(e) => setStaffForm({ ...staffForm, department: e.target.value })}><option value="">Unassigned</option>{departmentQuery.data?.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</SelectField>
        <FormField label="Job title" value={staffForm.job_title} onChange={(e) => setStaffForm({ ...staffForm, job_title: e.target.value })} />
        <FormField label="License number" value={staffForm.license_number} onChange={(e) => setStaffForm({ ...staffForm, license_number: e.target.value })} />
        <SelectField label="Employment status" value={staffForm.employment_status} onChange={(e) => setStaffForm({ ...staffForm, employment_status: e.target.value })}><option value="ACTIVE">Active</option><option value="ON_LEAVE">On leave</option><option value="INACTIVE">Inactive</option></SelectField>
        <label className="check-field"><input type="checkbox" checked={staffForm.account_active} onChange={(e) => setStaffForm({ ...staffForm, account_active: e.target.checked })} /><span><strong>Account can sign in</strong><small>Turn off access without deleting historical records.</small></span></label>
        <div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" isLoading={updateMutation.isPending}>Save staff access</Button></div>
      </form>
    </Modal>
  </div>
}
