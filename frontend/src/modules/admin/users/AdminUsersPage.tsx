import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, UserCog } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { getSystemUsers, updateSystemUser } from './api'
import type { SystemUser } from './types'

export function AdminUsersPage() {
  const client = useQueryClient()
  const [selected, setSelected] = useState<SystemUser | null>(null)
  const [active, setActive] = useState(true)
  const [mustChange, setMustChange] = useState(false)
  const query = useQuery({ queryKey: ['system-users'], queryFn: getSystemUsers })
  const mutation = useMutation({ mutationFn: () => updateSystemUser(selected!.id, { is_active: active, must_change_password: mustChange }), onSuccess: async () => { setSelected(null); await Promise.all([client.invalidateQueries({ queryKey: ['system-users'] }), client.invalidateQueries({ queryKey: ['system-dashboard'] })]) } })
  const open = (user: SystemUser) => { mutation.reset(); setSelected(user); setActive(user.is_active); setMustChange(user.must_change_password) }
  return <div className="workspace-page"><PageHeader eyebrow="Identity administration" title="System users" description="Suspend accounts and require password changes without changing clinical or financial roles." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">System users could not be loaded.</Alert> : <section className="section-panel table-panel"><div className="table-scroll"><table className="data-table"><thead><tr><th>User</th><th>Role</th><th>Employee number</th><th>Last login</th><th>Status</th><th /></tr></thead><tbody>{query.data!.map((user) => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td>{user.role_label}</td><td>{user.employee_number || '—'}</td><td>{user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td><td><StatusBadge status={user.is_active ? 'ACTIVE' : 'INACTIVE'} label={user.must_change_password ? 'Password change required' : user.is_active ? 'Active' : 'Inactive'} /></td><td><Button variant="ghost" onClick={() => open(user)}><UserCog size={15} /> Manage</Button></td></tr>)}</tbody></table></div></section>}<Modal open={Boolean(selected)} onClose={() => setSelected(null)} title="Manage system access" description={selected ? `${selected.full_name} · ${selected.role_label}` : undefined}><label className="check-field"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /><span><strong>Account is active</strong><small>Inactive users cannot authenticate.</small></span></label><label className="check-field"><input type="checkbox" checked={mustChange} onChange={(event) => setMustChange(event.target.checked)} /><span><strong>Require password change</strong><small>Other API capabilities remain blocked until completed.</small></span></label>{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'User access could not be changed.'}</Alert>}<div className="modal__actions"><Button variant="secondary" onClick={() => setSelected(null)}>Cancel</Button><Button onClick={() => mutation.mutate()} isLoading={mutation.isPending}><ShieldCheck size={16} /> Save access</Button></div></Modal></div>
}
