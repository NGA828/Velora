export interface PersonReference { staff_id: string; name: string }
export interface DepartmentReference { id: string; name: string }
export interface Patient {
  id: string
  medical_record_number: string
  first_name: string
  last_name: string
  full_name: string
  date_of_birth: string
  age: number
  sex_at_birth: string
  status: string
  primary_doctor: PersonReference | null
  primary_nurse: PersonReference | null
  current_department: DepartmentReference | null
  active_guardian_count: number
  latest_vital_status: 'UNASSESSED' | 'STABLE' | 'CRITICAL' | null
  latest_vital_at: string | null
  created_at: string
}
export interface CareTeamMember { id: string; staff_id: string; user_id: string; full_name: string; role: string; job_title: string; is_primary: boolean; starts_at: string }
export interface CareEpisode { id: string; episode_number: string; episode_type: string; episode_type_label: string; department: string; department_name: string; admission_reason: string; admitted_at: string; discharged_at: string | null; status: string }
export interface PatientDetail extends Patient {
  gender_identity: string
  blood_type: string
  phone: string
  email: string
  address: string
  emergency_contact_name: string
  emergency_contact_phone: string
  care_team: CareTeamMember[]
  active_episode: CareEpisode | null
  medical_file: { id: string; file_number: string; status: string } | null
  updated_at: string
}
export interface PatientDashboard { role: string; total_assigned: number; active_episodes: number; without_guard: number; critical_patients: number; unassessed_patients: number; by_status: Record<string, number>; recent_patients: Patient[] }
export interface ClinicalStaff { id: string; user_id: string; full_name: string; email: string; role: string; role_label: string; employee_number: string; department: string | null; department_name?: string | null; job_title: string; employment_status: string }
export interface Department { id: string; code: string; name: string; is_active: boolean }
export interface GuardianAccess { id: string; patient: string; guardian_profile: string | null; email: string; full_name: string; relationship: string; status: string; can_view_medical_file: boolean; can_answer_monitoring: boolean; can_decide_transfers: boolean; can_view_billing: boolean; invited_at: string; accepted_at: string | null; granted_at: string | null; revoked_at: string | null }
