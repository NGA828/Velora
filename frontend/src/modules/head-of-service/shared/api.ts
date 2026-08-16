import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'

export async function listRecords<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T[]> {
  const response = await apiClient.get<PaginatedResponse<T>>(path, { params: { page_size: 100, ...params } })
  return response.data.data
}

export async function getRecord<T>(path: string): Promise<T> {
  const response = await apiClient.get<T>(path)
  return response.data
}

export async function createRecord<T>(path: string, payload: unknown): Promise<T> {
  await prepareCsrf()
  const response = await apiClient.post<T>(path, payload)
  return response.data
}

export async function updateRecord<T>(path: string, id: string, payload: unknown): Promise<T> {
  await prepareCsrf()
  const response = await apiClient.patch<T>(`${path}${id}/`, payload)
  return response.data
}

export async function putRecord<T>(path: string, payload: unknown): Promise<T> {
  await prepareCsrf()
  const response = await apiClient.put<T>(path, payload)
  return response.data
}

export async function postAction<T>(path: string): Promise<T> {
  await prepareCsrf()
  const response = await apiClient.post<T>(path)
  return response.data
}
