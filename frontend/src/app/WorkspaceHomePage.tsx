import { Check, KeyRound, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'

import { useSession } from '../modules/auth/hooks/use-session'
import { capabilityLabels, roleContent } from '../shared/lib/role-content'

export function WorkspaceHomePage() {
  const { data } = useSession()
  const user = data!.user
  const content = roleContent[user.role]

  useEffect(() => {
    document.title = `${user.role_label} workspace · Velora`
  }, [user.role_label])

  if (user.role === 'ADMIN') return <Navigate to="/admin-system" replace />
  if (user.role === 'ACCOUNTING') return <Navigate to="/accounting" replace />
  if (user.role === 'HEAD_OF_SERVICE') return <Navigate to="/head-of-service" replace />
  if (user.role === 'DOCTOR') return <Navigate to="/doctor" replace />
  if (user.role === 'NURSE') return <Navigate to="/nurse" replace />
  if (user.role === 'PATIENT_GUARD') return <Navigate to="/patient-guard" replace />

  return (
    <div className="workspace-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">{content.eyebrow}</p>
          <h1>Good day, {user.first_name}.</h1>
          <p>{content.heading}</p>
        </div>
        <span className="status-pill status-pill--success"><Check size={15} /> Account active</span>
      </header>

      <section className="welcome-panel">
        <div className="welcome-panel__copy">
          <span className="welcome-panel__icon"><ShieldCheck aria-hidden="true" /></span>
          <div>
            <p className="eyebrow eyebrow--light">Foundation secured</p>
            <h2>Your role and session are protected.</h2>
            <p>{content.description}</p>
          </div>
        </div>
        <div className="welcome-panel__facts">
          <div><UserRound aria-hidden="true" /><span><small>Current role</small><strong>{user.role_label}</strong></span></div>
          <div><KeyRound aria-hidden="true" /><span><small>Authentication</small><strong>Secure server session</strong></span></div>
        </div>
      </section>

      <div className="workspace-grid">
        <section className="section-panel">
          <div className="section-panel__heading">
            <div>
              <p className="eyebrow">Access boundary</p>
              <h2>Your authorized responsibilities</h2>
            </div>
            <span>{user.capabilities.length} capabilities</span>
          </div>
          <ul className="capability-list">
            {user.capabilities.map((capability) => (
              <li key={capability}>
                <span><Check size={15} aria-hidden="true" /></span>
                {capabilityLabels[capability] ?? capability}
              </li>
            ))}
          </ul>
        </section>

        <aside className="section-panel section-panel--quiet">
          <p className="eyebrow">Privacy boundary</p>
          <h2>Access follows responsibility</h2>
          <p>
            Your role opens only the functions assigned to it. Patient information will also require
            a direct care or Guard relationship; knowing a record identifier is never enough.
          </p>
          <div className="privacy-note">
            <ShieldCheck size={19} aria-hidden="true" />
            <span><strong>Protected by design</strong><small>Unauthorized requests are rejected and auditable.</small></span>
          </div>
        </aside>
      </div>
    </div>
  )
}
