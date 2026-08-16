import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { CatalogItem, TransferRequest } from './types'

export async function getTransferCatalog(path: 'specialties' | 'services' | 'clinical-conditions'): Promise<CatalogItem[]> {
  return (await apiClient.get<PaginatedResponse<CatalogItem>>(`/hospital/${path}/`, { params: { is_active: 'true', page_size: 100 } })).data.data
}
export async function getTransfers(patient?: string): Promise<TransferRequest[]> {
  return (await apiClient.get<PaginatedResponse<TransferRequest>>('/transfer-requests/', { params: { patient, page_size: 100 } })).data.data
}
export async function createTransfer(payload: unknown): Promise<TransferRequest> { await prepareCsrf(); return (await apiClient.post<TransferRequest>('/transfer-requests/', payload)).data }
export async function generateTransferRecommendations(id: string): Promise<TransferRequest> { await prepareCsrf(); return (await apiClient.post<TransferRequest>(`/transfer-requests/${id}/recommend/`)).data }
export async function submitTransfer(id: string, hospital: string): Promise<TransferRequest> { await prepareCsrf(); return (await apiClient.post<TransferRequest>(`/transfer-requests/${id}/submit/`, { hospital })).data }
export async function decideTransfer(id: string, decision: 'APPROVE' | 'REJECT', reason: string): Promise<TransferRequest> { await prepareCsrf(); return (await apiClient.post<TransferRequest>(`/transfer-requests/${id}/decide/`, { decision, reason })).data }
export async function sendTransferPackage(id: string): Promise<TransferRequest> { await prepareCsrf(); return (await apiClient.post<TransferRequest>(`/transfer-requests/${id}/send-package/`)).data }
