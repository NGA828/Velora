export type VitalStatus = 'UNASSESSED' | 'STABLE' | 'CRITICAL'

export interface VitalScore {
  status: VitalStatus
  stability_percent: number | null
  criticality_percent: number | null
  assessed_metric_count: number
  critical_metric_count: number
}

export function displayPercent(score: VitalScore): number | null {
  if (score.status === 'CRITICAL' && score.criticality_percent != null) {
    return score.criticality_percent
  }
  if (score.stability_percent != null) {
    return score.stability_percent
  }
  return null
}

export function displayPercentLabel(score: VitalScore): string {
  const percent = displayPercent(score)
  if (percent == null) return 'Not scored'
  return score.status === 'CRITICAL' ? `${percent}% critical` : `${percent}% stable`
}

export function scoreDetail(score: VitalScore): string {
  if (score.assessed_metric_count <= 0) {
    return score.status === 'UNASSESSED'
      ? 'No approved rule coverage was available for these measurements.'
      : 'No scored vital signs were included in this observation.'
  }
  if (score.critical_metric_count > 0) {
    return `${score.critical_metric_count} of ${score.assessed_metric_count} assessed vitals matched a configured critical rule.`
  }
  if (score.status === 'UNASSESSED') {
    return `${score.stability_percent ?? 0}% of the assessed vitals are within range, but rule coverage is incomplete.`
  }
  return `All ${score.assessed_metric_count} assessed vitals are within the hospital’s configured range.`
}

export function patientScore(patient: {
  latest_vital_status: VitalStatus | null
  latest_vital_stability_percent: number | null
  latest_vital_criticality_percent: number | null
  latest_vital_assessed_metric_count: number | null
  latest_vital_critical_metric_count: number | null
}): VitalScore | null {
  if (!patient.latest_vital_status) return null
  return {
    status: patient.latest_vital_status,
    stability_percent: patient.latest_vital_stability_percent,
    criticality_percent: patient.latest_vital_criticality_percent,
    assessed_metric_count: patient.latest_vital_assessed_metric_count ?? 0,
    critical_metric_count: patient.latest_vital_critical_metric_count ?? 0,
  }
}
