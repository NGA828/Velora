import axios from 'axios'

import { normalizeApiError } from './errors'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  timeout: 15_000,
  xsrfCookieName: 'velora_csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(normalizeApiError(error)),
)
