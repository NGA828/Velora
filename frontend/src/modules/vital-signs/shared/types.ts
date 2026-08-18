export interface VitalMetric {
  id: string
  code: string
  name: string
  unit: string
  decimal_places: number
  description: string
  display_order: number
  contributes_to_assessment: boolean
  is_active: boolean
}
export interface RuleEvaluation {
  id: string
  matched: boolean
  measured_value: string
  rule_name_snapshot: string
  metric_name_snapshot: string
  metric_unit_snapshot: string
  operator_snapshot: string
  lower_value_snapshot: string | null
  upper_value_snapshot: string | null
  explanation: string
}
export interface VitalValue {
  id: string
  metric: string
  metric_name: string
  metric_code: string
  unit: string
  value: string
  contributes_to_assessment: boolean
  is_critical: boolean
  evaluations: RuleEvaluation[]
}
export interface VitalObservation {
  id: string
  patient: string
  patient_name: string
  care_episode: string
  observed_at: string
  recorded_by_name: string
  status: 'UNASSESSED' | 'STABLE' | 'CRITICAL'
  status_label: string
  stability_percent: number | null
  criticality_percent: number | null
  assessed_metric_count: number
  critical_metric_count: number
  notes: string
  analyzed_at: string
  rule_set_name_snapshot: string
  rule_set_version_snapshot: number | null
  values: VitalValue[]
  created_at: string
}
