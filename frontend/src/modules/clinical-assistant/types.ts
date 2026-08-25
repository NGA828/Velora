export type AssistantRole = 'user' | 'assistant' | 'system'

export interface AssistantMessage {
  id: string
  role: AssistantRole
  content: string
  validation_passed: boolean
  created_at: string
}

export interface AssistantSession {
  id: string
  patient: string
  patient_name: string
  title: string
  is_active: boolean
  created_at: string
  updated_at: string
  messages: AssistantMessage[]
}

export interface ContextSummary {
  vital_status?: 'STABLE' | 'CRITICAL' | 'UNASSESSED'
  icu_eligible?: boolean
  icu_score?: number | null
  specialist_status?: 'AVAILABLE' | 'OVERLOADED' | 'ABSENT' | null
  icu_bed_status?: 'AVAILABLE' | 'OVERLOADED' | 'UNAVAILABLE' | null
}

export interface ChatResponse {
  session_id: string
  message: AssistantMessage
  fallback: boolean
  context_summary: ContextSummary
}

export interface ClinicalContext {
  context_role: string
  generated_at: string
  patient: {
    id?: string
    full_name?: string
    first_name?: string
    medical_record_number: string
    age?: number | null
    sex_at_birth?: string
    gender_identity?: string
    blood_type?: string
  }
  episode?: {
    department?: string
    episode_type?: string
    admission_reason?: string
    admitted_at?: string | null
  }
  latest_vitals?: {
    observation_id?: string
    observed_at: string
    status: string
    stability_percent?: number | null
    criticality_percent?: number | null
    rule_set?: string
    measurements?: Record<string, any>
    critical_rules_matched?: Array<{
      metric: string
      rule: string
      operator?: string
      threshold?: string
      measured_value: number
      explanation: string
    }>
    notes?: string
  } | null
  vital_trends?: Array<{
    observed_at: string
    status: string
    stability_percent?: number | null
    criticality_percent?: number | null
  }>
  icu_assessment?: {
    recommendation_id?: string
    eligible: boolean
    readiness_score?: number
    specialist_status?: string
    icu_bed_status?: string
    official_recommendation?: string
    explanation: string
    source: string
  } | null
  diagnoses?: Array<{
    code?: string
    name: string
    status: string
  }>
  allergies?: Array<{
    substance: string
    severity: string
    reaction?: string
  }>
  active_treatment_plans?: Array<{
    title: string
    instructions: string
  }>
  active_prescriptions?: Array<{
    medication: string
    dose: string
    frequency: string
    instructions?: string
  }>
}
