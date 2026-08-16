export type UserRole =
  | 'ADMIN'
  | 'HEAD_OF_SERVICE'
  | 'DOCTOR'
  | 'NURSE'
  | 'PATIENT_GUARD'
  | 'ACCOUNTING'

export interface SessionUser {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: UserRole
  role_label: string
  capabilities: string[]
  must_change_password: boolean
}

export interface SessionResponse {
  user: SessionUser
}
