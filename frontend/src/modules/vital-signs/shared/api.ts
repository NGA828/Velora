import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { VitalMetric, VitalObservation } from './types'

export async function getVitalMetrics(): Promise<VitalMetric[]> {
  return (await apiClient.get<PaginatedResponse<VitalMetric>>('/vital-metrics/', { params: { page_size: 100 } })).data.data
}
export async function getVitalObservations(patient: string): Promise<VitalObservation[]> {
  return (await apiClient.get<PaginatedResponse<VitalObservation>>('/vital-observations/', { params: { patient, page_size: 100 } })).data.data
}
export async function getIcuRecommendations(): Promise<VitalObservation[]> {
  return (await apiClient.get<PaginatedResponse<VitalObservation>>('/vital-observations/icu-recommendations/', { params: { page_size: 100 } })).data.data
}
export async function createVitalObservation(payload: unknown): Promise<VitalObservation> {
  await prepareCsrf()
  return (await apiClient.post<VitalObservation>('/vital-observations/', payload)).data
}
