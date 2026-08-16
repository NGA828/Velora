import { apiClient } from './client'

let csrfRequest: Promise<void> | null = null

export function prepareCsrf(): Promise<void> {
  if (!csrfRequest) {
    csrfRequest = apiClient
      .get<{ csrf_token: string }>('/auth/csrf/')
      .then((response) => {
        apiClient.defaults.headers.common['X-CSRFToken'] = response.data.csrf_token
      })
      .finally(() => {
        csrfRequest = null
      })
  }
  return csrfRequest
}
