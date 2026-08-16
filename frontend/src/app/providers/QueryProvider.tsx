import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import type { ReactNode } from 'react'

import { AppApiError } from '../../shared/api/errors'

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Keep recently visited screens responsive instead of refetching the same data
            // on every route transition. Mutations and realtime events still invalidate
            // their affected query keys immediately.
            staleTime: 15_000,
            refetchOnWindowFocus: false,
            retry: (failureCount, error) =>
              error instanceof AppApiError && error.status >= 500 && failureCount < 1,
          },
          mutations: { retry: false },
        },
      }),
  )

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
