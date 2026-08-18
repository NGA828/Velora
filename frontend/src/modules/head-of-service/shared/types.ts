export interface HospitalDashboard {
  staff: { active_clinical: number; pending_invitations: number }
  operations: { departments: number; available_beds: number; total_beds: number; resources_unavailable: number }
  transfers: { external_hospitals: number; incomplete_profiles: number }
  hospital_profile_configured: boolean
  generated_at: string
}

export interface Department { id: string; code: string; name: string; description: string; location: string; phone: string; is_active: boolean; parent: string | null; parent_name?: string | null; head_name?: string | null; staff_count: number }
export interface HospitalProfile { id: string; legal_name: string; display_name: string; registration_number: string; address: string; city: string; region: string; country: string; email: string; phone: string; website: string; timezone: string; billing_currency: string }
export interface Staff { id: string; user_id: string; email: string; full_name: string; role: string; role_label: string; account_active: boolean; employee_number: string; department: string | null; department_name?: string | null; job_title: string; license_number: string; employment_status: string }
export interface Invitation { id: string; email: string; intended_role: string; intended_role_label: string; invited_by_name: string; expires_at: string; status: string; created_at: string }
export interface Specialty { id: string; code: string; name: string; description: string; is_active: boolean; condition_count: number }
export interface ClinicalCondition { id: string; coding_system: string; code: string; name: string; description: string; is_active: boolean; specialty_count: number }
export interface SpecialtyMapping { id: string; specialty: string; specialty_name: string; condition: string; condition_name: string; condition_code: string; match_weight: string; notes: string }
export interface ServiceDefinition { id: string; code: string; name: string; category: string; description: string; is_active: boolean; department_count: number }
export interface ServiceAvailability { id: string; service: string; service_name: string; department: string; department_name: string; availability_status: string; notes: string }
export interface Room { id: string; code: string; department: string; department_name: string; floor: string; room_type: string; status: string; bed_count: number; available_bed_count: number }
export interface Bed { id: string; code: string; room: string; room_code: string; department_name: string; status: string; notes: string }
export interface Resource { id: string; asset_code: string; name: string; category: string; department: string; department_name: string; quantity_total: number; quantity_available: number; status: string; notes: string }
export interface ExternalHospital { id: string; name: string; address: string; city: string; region: string; country: string; latitude: string | null; longitude: string | null; email: string; phone: string; transfer_email: string; notes: string; is_active: boolean; specialty_count: number; service_count: number; specialist_count: number; transfer_ready: boolean }
export interface ExternalSpecialty { id: string; external_hospital: string; specialty: string; specialty_name: string; availability_status: string; notes: string }
export interface ExternalService { id: string; external_hospital: string; service: string; service_name: string; availability_status: string; notes: string }
export interface ExternalSpecialist { id: string; external_hospital: string; specialty: string; specialty_name: string; full_name: string; title: string; phone: string; email: string; is_active: boolean }
export interface VitalMetric { id: string; code: string; name: string; unit: string; decimal_places: number; description: string; display_order: number; contributes_to_assessment: boolean; is_active: boolean }
export interface VitalRuleSet { id: string; name: string; version: number; description: string; status: string; rule_count: number; approved_by_name?: string | null; effective_from?: string | null; effective_to?: string | null }
export interface VitalRule { id: string; rule_set: string; metric: string; metric_name: string; metric_unit: string; name: string; operator: string; operator_label: string; lower_value: string | null; upper_value: string | null; priority: number; explanation: string; is_active: boolean }
