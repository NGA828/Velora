import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useSession } from '../../modules/auth/hooks/use-session'
import { AppApiError } from '../../shared/api/errors'
import { Alert } from '../../shared/ui/feedback/Alert'
import { FullPageLoader } from '../../shared/ui/feedback/FullPageLoader'
import { Brand } from '../../shared/ui/navigation/Brand'
import { Button } from '../../shared/ui/actions/Button'

export function SessionGate() {
  const location = useLocation()
  const session = useSession()

  if (session.isPending) return <FullPageLoader />

  if (session.error instanceof AppApiError && [401, 403].includes(session.error.status)) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (session.isError) {
    return (
      <main className="standalone-state">
        <Brand />
        <Alert tone="critical" title="We could not open your workspace">
          {session.error instanceof Error
            ? session.error.message
            : 'Check your connection and try again.'}
        </Alert>
        <Button onClick={() => void session.refetch()}>Try again</Button>
      </main>
    )
  }

  return <Outlet />
}
