import { Link } from 'react-router-dom'

import { Brand } from '../../shared/ui/navigation/Brand'

export function NotFoundPage() {
  return (
    <main className="standalone-state">
      <Brand />
      <p className="eyebrow">404</p>
      <h1>Page not found</h1>
      <p>The address may be incorrect or the page may not be available to your role.</p>
      <Link className="button button--primary" to="/">Return to workspace</Link>
    </main>
  )
}
