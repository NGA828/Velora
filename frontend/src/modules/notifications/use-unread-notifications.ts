import { useQuery } from '@tanstack/react-query'

import { getNotifications } from './api'

/**
 * Live unread-notification count for the sidebar bell. Refreshed whenever a
 * notification.* realtime event arrives (RealtimeProvider invalidates the
 * ['notifications', 'unread'] key) and on a slow background interval as a
 * safety net.
 */
export function useUnreadNotificationCount(): number {
  const query = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => getNotifications(true),
    refetchInterval: 60_000,
  })
  return query.data?.length ?? 0
}
