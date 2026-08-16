import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { AuditEvent, SystemDashboard, SystemUser } from './types'

export async function getSystemDashboard(): Promise<SystemDashboard> { return (await apiClient.get<SystemDashboard>('/system/dashboard/')).data }
export async function getSystemUsers(): Promise<SystemUser[]> { return (await apiClient.get<PaginatedResponse<SystemUser>>('/system/users/', { params: { page_size: 100 } })).data.data }
export async function updateSystemUser(id: string, payload: unknown): Promise<SystemUser> { await prepareCsrf(); return (await apiClient.patch<SystemUser>(`/system/users/${id}/`, payload)).data }
export async function getAuditEvents(action = ''): Promise<AuditEvent[]> { return (await apiClient.get<PaginatedResponse<AuditEvent>>('/system/audit/', { params: { page_size: 100, action: action || undefined } })).data.data }
