import axios from 'axios'

export type ApiFieldErrors = Record<string, unknown>

interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    fields?: ApiFieldErrors
    request_id?: string | null
  }
}

export class AppApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: ApiFieldErrors
  readonly requestId?: string

  constructor(options: {
    message: string
    status?: number
    code?: string
    fields?: ApiFieldErrors
    requestId?: string
  }) {
    super(options.message)
    this.name = 'AppApiError'
    this.status = options.status ?? 0
    this.code = options.code ?? 'network_error'
    this.fields = options.fields ?? {}
    this.requestId = options.requestId
  }
}

export function normalizeApiError(error: unknown): AppApiError {
  if (error instanceof AppApiError) return error
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const payload = error.response?.data?.error
    return new AppApiError({
      message:
        payload?.message ??
        (error.response
          ? 'The request could not be completed.'
          : 'Unable to reach the hospital system. Check your connection and try again.'),
      status: error.response?.status,
      code: payload?.code,
      fields: payload?.fields,
      requestId: payload?.request_id ?? undefined,
    })
  }
  return new AppApiError({ message: 'An unexpected error occurred.' })
}

export function firstFieldError(error: AppApiError | undefined, field: string): string | undefined {
  if (!error) return undefined
  const value = error.fields[field]
  if (typeof value === 'string') return value
  if (Array.isArray(value) && value.length > 0) return String(value[0])
  return undefined
}
