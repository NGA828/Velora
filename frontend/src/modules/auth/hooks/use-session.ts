import { useQuery } from '@tanstack/react-query'

import { getSession } from '../api/auth-api'

export const sessionQueryKey = ['auth', 'session'] as const

export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: getSession,
    staleTime: 60_000,
    retry: false,
  })
}
