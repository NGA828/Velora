import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { SessionResponse } from '../types/session'

export interface LoginInput {
  email: string
  password: string
}

export interface InvitationInput {
  token: string
  first_name: string
  last_name: string
  phone?: string
  password: string
  confirm_password: string
}

export interface ChangePasswordInput {
  old_password: string
  new_password: string
  confirm_password: string
}

export async function getSession(): Promise<SessionResponse> {
  const response = await apiClient.get<SessionResponse>('/auth/session/')
  return response.data
}

export async function login(input: LoginInput): Promise<SessionResponse> {
  await prepareCsrf()
  const response = await apiClient.post<SessionResponse>('/auth/login/', input)
  return response.data
}

export async function logout(): Promise<void> {
  await prepareCsrf()
  await apiClient.post('/auth/logout/')
}

export async function acceptInvitation(input: InvitationInput): Promise<SessionResponse> {
  await prepareCsrf()
  const response = await apiClient.post<SessionResponse>('/auth/invitations/accept/', input)
  return response.data
}

export async function changePassword(input: ChangePasswordInput): Promise<SessionResponse> {
  await prepareCsrf()
  const response = await apiClient.post<SessionResponse>('/auth/password/change/', input)
  return response.data
}
