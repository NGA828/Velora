import type { ReactNode } from 'react'
import { LockKeyhole, Network, ShieldCheck } from 'lucide-react'

import { Brand } from '../../shared/ui/navigation/Brand'

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="auth-layout">
      <section className="auth-story" aria-label="About Velora">
        <Brand inverse />
        <div className="auth-story__content">
          <p className="eyebrow eyebrow--light">Connected hospital care</p>
          <h1>One secure workspace for every care handoff.</h1>
          <p>
            Velora keeps staff, patient care and authorized family participation connected without
            blurring clinical boundaries.
          </p>
          <div className="auth-story__principles">
            <div>
              <ShieldCheck aria-hidden="true" />
              <span><strong>Role protected</strong><small>Access follows real care relationships.</small></span>
            </div>
            <div>
              <Network aria-hidden="true" />
              <span><strong>Workflow connected</strong><small>Actions continue across the care team.</small></span>
            </div>
            <div>
              <LockKeyhole aria-hidden="true" />
              <span><strong>Patient conscious</strong><small>Sensitive information stays scoped.</small></span>
            </div>
          </div>
        </div>
        <p className="auth-story__footer">Clinical operations · Secure by design</p>
      </section>
      <section className="auth-panel">
        <div className="auth-panel__mobile-brand"><Brand /></div>
        {children}
      </section>
    </main>
  )
}
