import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { Medication, MedicationDose, Prescription } from './types'

export async function getMedications(activeOnly = false): Promise<Medication[]> {
  return (await apiClient.get<PaginatedResponse<Medication>>('/medications/', { params: { page_size: 100, is_active: activeOnly ? 'true' : undefined } })).data.data
}
export async function createMedication(payload: unknown): Promise<Medication> {
  await prepareCsrf()
  return (await apiClient.post<Medication>('/medications/', payload)).data
}
export async function updateMedication(id: string, payload: unknown): Promise<Medication> {
  await prepareCsrf()
  return (await apiClient.patch<Medication>(`/medications/${id}/`, payload)).data
}
export async function getPrescriptions(patient?: string): Promise<Prescription[]> {
  return (await apiClient.get<PaginatedResponse<Prescription>>('/prescriptions/', { params: { page_size: 100, patient } })).data.data
}
export async function createPrescription(payload: unknown): Promise<Prescription> {
  await prepareCsrf()
  return (await apiClient.post<Prescription>('/prescriptions/', payload)).data
}
export async function activatePrescription(id: string): Promise<Prescription> {
  await prepareCsrf()
  return (await apiClient.post<Prescription>(`/prescriptions/${id}/activate/`)).data
}
export async function cancelPrescription(id: string, reason: string): Promise<Prescription> {
  await prepareCsrf()
  return (await apiClient.post<Prescription>(`/prescriptions/${id}/cancel/`, { reason })).data
}
export async function completePrescription(id: string): Promise<Prescription> {
  await prepareCsrf()
  return (await apiClient.post<Prescription>(`/prescriptions/${id}/complete/`)).data
}
export async function getDueDoses(): Promise<MedicationDose[]> {
  return (await apiClient.get<PaginatedResponse<MedicationDose>>('/medication-doses/due/', { params: { page_size: 100 } })).data.data
}
export async function getMedicationDoses(status?: string): Promise<MedicationDose[]> {
  return (await apiClient.get<PaginatedResponse<MedicationDose>>('/medication-doses/', { params: { page_size: 100, status } })).data.data
}
export async function recordDoseOutcome(id: string, outcome: 'administer' | 'miss' | 'refuse', notes: string): Promise<MedicationDose> {
  await prepareCsrf()
  return (await apiClient.post<MedicationDose>(`/medication-doses/${id}/${outcome}/`, { notes })).data
}
