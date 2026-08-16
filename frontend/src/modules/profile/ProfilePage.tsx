import { Mail, Phone, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import { useSession } from '../auth/hooks/use-session'

export function ProfilePage() {
  const { data } = useSession()
  const user = data!.user

  useEffect(() => {
    document.title = 'Profile & security · Velora'
  }, [])

  return (
    <div className="workspace-page workspace-page--narrow">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Profile & security</h1>
          <p>Review the identity attached to your hospital access.</p>
        </div>
      </header>

      <section className="profile-card">
        <div className="profile-card__identity">
          <span className="profile-card__avatar"><UserRound aria-hidden="true" /></span>
          <div><h2>{user.full_name}</h2><p>{user.role_label}</p></div>
          <span className="status-pill status-pill--success">Active</span>
        </div>
        <dl className="profile-details">
          <div><dt><Mail size={17} /> Email address</dt><dd>{user.email}</dd></div>
          <div><dt><Phone size={17} /> Telephone</dt><dd>{user.phone || 'Not provided'}</dd></div>
          <div><dt><ShieldCheck size={17} /> Access role</dt><dd>{user.role_label}</dd></div>
        </dl>
      </section>

      <section className="section-panel security-panel">
        <div>
          <p className="eyebrow">Password</p>
          <h2>Keep your access private</h2>
          <p>Change your password if it may have been seen or reused elsewhere.</p>
        </div>
        <Link className="button button--secondary" to="/change-password">Change password</Link>
      </section>
    </div>
  )
}
