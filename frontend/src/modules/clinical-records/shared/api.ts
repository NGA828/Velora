import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { Allergy, ClinicalCondition, ClinicalNote, Diagnosis, HistoryEntry, TreatmentPlan } from './types'

async function list<T>(path: string, patient: string): Promise<T[]> {
  return (await apiClient.get<PaginatedResponse<T>>(path, { params: { patient, page_size: 100 } })).data.data
}
export const getAllergies = (patient: string) => list<Allergy>('/allergies/', patient)
export const getHistory = (patient: string) => list<HistoryEntry>('/medical-history/', patient)
export const getDiagnoses = (patient: string) => list<Diagnosis>('/diagnoses/', patient)
export const getTreatmentPlans = (patient: string) => list<TreatmentPlan>('/treatment-plans/', patient)
export const getClinicalNotes = (patient: string) => list<ClinicalNote>('/clinical-notes/', patient)
export async function getClinicalConditions(): Promise<ClinicalCondition[]> {
  return (await apiClient.get<PaginatedResponse<ClinicalCondition>>('/hospital/clinical-conditions/', { params: { is_active: 'true', page_size: 100 } })).data.data
}
export async function createClinicalRecord<T>(path: string, payload: unknown): Promise<T> {
  await prepareCsrf()
  return (await apiClient.post<T>(path, payload)).data
}
export async function signClinicalNote(id: string): Promise<ClinicalNote> {
  await prepareCsrf()
  return (await apiClient.post<ClinicalNote>(`/clinical-notes/${id}/sign/`)).data
}
