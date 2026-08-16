import { Navigate, Outlet } from 'react-router-dom'

import { useSession } from '../../modules/auth/hooks/use-session'

export function RequirePasswordReady() {
  const { data } = useSession()
  if (data?.user.must_change_password) {
    return <Navigate to="/change-password" replace />
  }
  return <Outlet />
}
