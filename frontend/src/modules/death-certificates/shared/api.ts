import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { DeathCertificate } from './types'

export async function getDeathCertificates(patient?: string): Promise<DeathCertificate[]> { return (await apiClient.get<PaginatedResponse<DeathCertificate>>('/death-certificates/', { params: { patient, page_size: 100 } })).data.data }
export async function createDeathCertificate(payload: unknown): Promise<DeathCertificate> { await prepareCsrf(); return (await apiClient.post<DeathCertificate>('/death-certificates/', payload)).data }
export async function issueDeathCertificate(id: string): Promise<DeathCertificate> { await prepareCsrf(); return (await apiClient.post<DeathCertificate>(`/death-certificates/${id}/issue/`)).data }
export async function voidDeathCertificate(id: string, reason: string): Promise<DeathCertificate> { await prepareCsrf(); return (await apiClient.post<DeathCertificate>(`/death-certificates/${id}/void/`, { reason })).data }
export async function getPrintableDeathCertificate(id: string): Promise<DeathCertificate> { return (await apiClient.get<DeathCertificate>(`/death-certificates/${id}/printable/`)).data }
