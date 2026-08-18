import { describe, expect, it } from 'vitest'

import { displayPercent, displayPercentLabel, scoreDetail } from './stability'

describe('vital stability scoring display', () => {
  it('shows a stability percentage when the observation is stable', () => {
    const score = {
      status: 'STABLE' as const,
      stability_percent: 100,
      criticality_percent: 0,
      assessed_metric_count: 5,
      critical_metric_count: 0,
    }
    expect(displayPercent(score)).toBe(100)
    expect(displayPercentLabel(score)).toBe('100% stable')
    expect(scoreDetail(score)).toContain('All 5 assessed vitals')
  })

  it('shows a criticality percentage when any vital matched a critical rule', () => {
    const score = {
      status: 'CRITICAL' as const,
      stability_percent: 80,
      criticality_percent: 20,
      assessed_metric_count: 5,
      critical_metric_count: 1,
    }
    expect(displayPercent(score)).toBe(20)
    expect(displayPercentLabel(score)).toBe('20% critical')
    expect(scoreDetail(score)).toBe('1 of 5 assessed vitals matched a configured critical rule.')
  })

  it('does not invent a percentage when nothing could be scored', () => {
    const score = {
      status: 'UNASSESSED' as const,
      stability_percent: null,
      criticality_percent: null,
      assessed_metric_count: 0,
      critical_metric_count: 0,
    }
    expect(displayPercent(score)).toBeNull()
    expect(displayPercentLabel(score)).toBe('Not scored')
  })
})
