import { apiClient } from '../../shared/api/client'
import { prepareCsrf } from '../../shared/api/csrf'
import type { PaginatedResponse } from '../../shared/api/pagination'
import type { Notification } from './types'

export async function getNotifications(unread = false): Promise<Notification[]> {
  return (await apiClient.get<PaginatedResponse<Notification>>('/notifications/', { params: { unread: unread || undefined, page_size: 100 } })).data.data
}
export async function markNotificationRead(id: string): Promise<Notification> {
  await prepareCsrf()
  return (await apiClient.post<Notification>(`/notifications/${id}/read/`)).data
}
export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  await prepareCsrf()
  return (await apiClient.post<{ updated: number }>('/notifications/read-all/')).data
}
