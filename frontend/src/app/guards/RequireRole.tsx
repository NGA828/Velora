import { Navigate, Outlet } from 'react-router-dom'

import { useSession } from '../../modules/auth/hooks/use-session'
import type { UserRole } from '../../modules/auth/types/session'

export function RequireRole({ roles }: { roles: UserRole[] }) {
  const { data } = useSession()
  if (!data || !roles.includes(data.user.role)) return <Navigate to="/" replace />
  return <Outlet />
}
