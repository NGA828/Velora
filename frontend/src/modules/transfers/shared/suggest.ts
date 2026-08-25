export interface RequirementDraft {
  key: string
  requirement_type: 'SPECIALTY' | 'SERVICE' | 'CONDITION'
  target: string
  weight: string
  is_mandatory: boolean
  source?: string
}

export interface TransferSuggestion {
  requirement_type: 'SPECIALTY' | 'SERVICE' | 'CONDITION'
  target: string
  label: string
  weight: string
  is_mandatory: boolean
  source: string
}

export function mergeSuggestions(current: RequirementDraft[], suggestions: TransferSuggestion[]): RequirementDraft[] {
  const merged = [...current]
  for (const item of suggestions) {
    const duplicate = merged.some(
      (existing) => existing.requirement_type === item.requirement_type && existing.target === item.target,
    )
    if (!duplicate) {
      merged.push({
        key: crypto.randomUUID(),
        requirement_type: item.requirement_type,
        target: item.target,
        weight: item.weight,
        is_mandatory: item.is_mandatory,
        source: item.source,
      })
    }
  }
  return merged
}
