import { Activity, BedDouble, BrainCircuit, ChevronDown, ChevronUp, Stethoscope } from 'lucide-react'
import { useState } from 'react'

import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import type { ClinicalContext } from '../types'

interface Props {
  context: ClinicalContext | null
  loading?: boolean
}

export function ClinicalContextBadge({ context, loading }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (loading) {
    return (
      <div className="assistant-context-panel assistant-context-panel--loading">
        <Activity size={16} className="spin" />
        <span>Loading verified clinical context...</span>
      </div>
    )
  }

  if (!context) return null

  const icu = context.icu_assessment
  const vitals = context.latest_vitals
  const isEligible = icu?.eligible ?? false
  const score = icu?.readiness_score ?? null

  return (
    <div className={`assistant-context-panel ${isEligible ? 'assistant-context-panel--critical' : ''}`}>
      <div className="assistant-context-panel__summary">
        <div className="assistant-context-panel__header">
          <div className="assistant-context-panel__title">
            <BrainCircuit size={17} />
            <strong>Clinical Context Snapshot</strong>
            {vitals?.status && <StatusBadge status={vitals.status} />}
          </div>
          <button
            type="button"
            className="assistant-context-toggle"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? <>Less <ChevronUp size={14} /></> : <>Details <ChevronDown size={14} /></>}
          </button>
        </div>

        <div className="assistant-context-chips">
          {icu && (
            <span className={`icu-chip ${isEligible ? 'icu-chip--eligible' : ''}`}>
              ICU: {isEligible ? 'Admission Recommended' : 'Standard Monitoring'}
            </span>
          )}
          {score !== null && (
            <span className="icu-chip">
              Readiness: <strong>{score}/100</strong>
            </span>
          )}
          {icu?.specialist_status && (
            <span className={`icu-chip icu-chip--${icu.specialist_status.toLowerCase()}`}>
              <Stethoscope size={13} /> {icu.specialist_status.replace('_', ' ').toLowerCase()}
            </span>
          )}
          {icu?.icu_bed_status && (
            <span className={`icu-chip icu-chip--${icu.icu_bed_status.toLowerCase()}`}>
              <BedDouble size={13} /> {icu.icu_bed_status.replace('_', ' ').toLowerCase()}
            </span>
          )}
        </div>
      </div>

      {expanded && (
        <div className="assistant-context-panel__expanded">
          {icu?.explanation && (
            <div className="assistant-context-detail">
              <span className="assistant-context-detail__label">CDSS Recommendation</span>
              <p>{icu.explanation}</p>
            </div>
          )}

          {vitals?.critical_rules_matched && vitals.critical_rules_matched.length > 0 && (
            <div className="assistant-context-detail">
              <span className="assistant-context-detail__label">Critical Rules Triggered</span>
              <ul>
                {vitals.critical_rules_matched.map((r, i) => (
                  <li key={i}>
                    <strong>{r.metric}</strong>: {r.explanation} (measured {r.measured_value})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {context.diagnoses && context.diagnoses.length > 0 && (
            <div className="assistant-context-detail">
              <span className="assistant-context-detail__label">Active Diagnoses</span>
              <p>{context.diagnoses.map((d) => d.name).join(', ')}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
