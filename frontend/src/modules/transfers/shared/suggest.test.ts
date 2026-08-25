import { describe, expect, it } from 'vitest'

import { mergeSuggestions } from './suggest'
import type { RequirementDraft, TransferSuggestion } from './suggest'

const draft = (overrides: Partial<RequirementDraft> = {}): RequirementDraft => ({
  key: crypto.randomUUID(),
  requirement_type: 'SPECIALTY',
  target: '',
  weight: '1.00',
  is_mandatory: true,
  ...overrides,
})

const suggestion = (overrides: Partial<TransferSuggestion> = {}): TransferSuggestion => ({
  requirement_type: 'SPECIALTY',
  target: 'c1',
  label: 'Cardiology',
  weight: '3.00',
  is_mandatory: false,
  source: 'Confirmed diagnosis I25',
  ...overrides,
})

describe('mergeSuggestions', () => {
  it('appends suggestions that are not already present, preserving existing rows', () => {
    const current = [draft({ requirement_type: 'CONDITION', target: 'c9' })]
    const merged = mergeSuggestions(current, [suggestion({ requirement_type: 'SPECIALTY', target: 'c1' })])
    expect(merged).toHaveLength(2)
    expect(merged[0]).toEqual(current[0])
    expect(merged[1]).toMatchObject({
      requirement_type: 'SPECIALTY',
      target: 'c1',
      weight: '3.00',
      is_mandatory: false,
      source: 'Confirmed diagnosis I25',
    })
  })

  it('dedupes by requirement type and target', () => {
    const current = [draft({ requirement_type: 'SPECIALTY', target: 'c1' })]
    const merged = mergeSuggestions(current, [
      suggestion({ requirement_type: 'SPECIALTY', target: 'c1' }),
      suggestion({ requirement_type: 'SPECIALTY', target: 'c2' }),
    ])
    expect(merged).toHaveLength(2)
    expect(merged.map((item) => item.target)).toEqual(['c1', 'c2'])
  })

  it('keeps distinct targets of the same requirement type', () => {
    const merged = mergeSuggestions([], [
      suggestion({ requirement_type: 'CONDITION', target: 'c1' }),
      suggestion({ requirement_type: 'CONDITION', target: 'c2' }),
    ])
    expect(merged).toHaveLength(2)
  })

  it('returns a new array and leaves the input untouched', () => {
    const current = [draft()]
    const snapshot = [...current]
    const merged = mergeSuggestions(current, [suggestion()])
    expect(merged).not.toBe(current)
    expect(current).toEqual(snapshot)
  })
})
