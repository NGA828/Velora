import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type {
  ClinicalStaff,
  Department,
  GuardianAccess,
  Patient,
  PatientDashboard,
  PatientDetail,
} from './types'

export async function getClinicalStaff(role: 'DOCTOR' | 'NURSE'): Promise<ClinicalStaff[]> {
  const response = await apiClient.get<PaginatedResponse<ClinicalStaff>>(
    '/staff/clinical-directory/',
    { params: { role, page_size: 100 } },
  )
  return response.data.data
}
export async function getActiveDepartments(): Promise<Department[]> {
  const response = await apiClient.get<PaginatedResponse<Department>>('/hospital/departments/', {
    params: { is_active: 'true', page_size: 100 },
  })
  return response.data.data
}
export async function getPatients(search = ''): Promise<Patient[]> {
  const response = await apiClient.get<PaginatedResponse<Patient>>('/patients/', { params: { page_size: 100, search: search || undefined } })
  return response.data.data
}
export async function getPatient(id: string): Promise<PatientDetail> {
  return (await apiClient.get<PatientDetail>(`/patients/${id}/`)).data
}
export async function getPatientDashboard(): Promise<PatientDashboard> {
  return (await apiClient.get<PatientDashboard>('/patients/dashboard/')).data
}
export async function createPatient(payload: unknown): Promise<PatientDetail> {
  await prepareCsrf()
  return (await apiClient.post<PatientDetail>('/patients/', payload)).data
}
export async function assignNurse(patientId: string, nurse: string): Promise<PatientDetail> {
  await prepareCsrf()
  return (await apiClient.post<PatientDetail>(`/patients/${patientId}/assign-nurse/`, { nurse })).data
}
export async function getGuardians(patientId: string): Promise<GuardianAccess[]> {
  return (await apiClient.get<GuardianAccess[]>(`/patients/${patientId}/guardians/`)).data
}
export async function inviteGuardian(patientId: string, payload: unknown): Promise<GuardianAccess> {
  await prepareCsrf()
  return (await apiClient.post<GuardianAccess>(`/patients/${patientId}/guardians/`, payload)).data
}
export async function revokeGuardian(patientId: string, accessId: string): Promise<GuardianAccess> {
  await prepareCsrf()
  return (await apiClient.post<GuardianAccess>(`/patients/${patientId}/guardians/${accessId}/revoke/`)).data
}
