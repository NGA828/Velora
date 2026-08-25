import { useQuery } from '@tanstack/react-query'
import { Activity, BedDouble, BrainCircuit, MessageSquare, ShieldAlert, Stethoscope, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { ClinicalAssistantDrawer } from '../../clinical-assistant/components/ClinicalAssistantDrawer'
import { getIcuRecommendations } from './api'
import type { IcuRecommendation } from './types'

const SPECIALIST_LABEL: Record<IcuRecommendation['specialist_status'], string> = {
  AVAILABLE: 'Specialist available',
  OVERLOADED: 'Specialist overloaded',
  ABSENT: 'Specialist absent',
}

const BED_LABEL: Record<IcuRecommendation['icu_bed_status'], string> = {
  AVAILABLE: 'ICU bed available',
  OVERLOADED: 'ICU at full capacity',
  UNAVAILABLE: 'No ICU beds configured',
}

function statusTone(value: string): 'good' | 'warn' | 'bad' {
  if (value === 'AVAILABLE') return 'good'
  if (value === 'OVERLOADED') return 'warn'
  return 'bad'
}

function RecommendationCard({
  patientId,
  patientName,
  observedAt,
  recommendation,
  onOpenAssistant,
  rolePath,
}: {
  patientId: string
  patientName: string
  observedAt: string
  recommendation: IcuRecommendation
  onOpenAssistant: () => void
  rolePath: 'doctor' | 'nurse'
}) {
  const specialistTone = statusTone(recommendation.specialist_status)
  const bedTone = statusTone(recommendation.icu_bed_status)
  return (
    <article className="icu-card">
      <header className="icu-card__header">
        <span className="icu-card__icon">
          <BrainCircuit />
        </span>
        <div>
          <h3>{patientName}</h3>
          <p>
            <UserRound size={14} /> {new Date(observedAt).toLocaleString()}
          </p>
        </div>
        {recommendation.eligible ? (
          <span className="icu-badge icu-badge--eligible">Recommended for ICU admission</span>
        ) : (
          <span className="icu-badge icu-badge--not-eligible">Not recommended</span>
        )}
      </header>
      <div className="icu-card__score">
        <div>
          <strong>{recommendation.score}</strong>
          <small>ICU readiness score</small>
        </div>
        <div className="icu-card__score-track" aria-hidden="true">
          <span style={{ width: `${recommendation.score}%` }} />
        </div>
      </div>
      <div className="icu-card__factors">
        <div className={`icu-factor icu-factor--${specialistTone}`}>
          <Stethoscope size={17} />
          <span>
            <strong>{SPECIALIST_LABEL[recommendation.specialist_status]}</strong>
            <small>{recommendation.specialist_status === 'AVAILABLE'
              ? 'Specialist physician is assigned and available.'
              : 'Specialist availability may delay urgent decisions — see explanation.'}</small>
          </span>
        </div>
        <div className={`icu-factor icu-factor--${bedTone}`}>
          <BedDouble size={17} />
          <span>
            <strong>{BED_LABEL[recommendation.icu_bed_status]}</strong>
            <small>{recommendation.icu_bed_status === 'AVAILABLE'
              ? 'Intensive care capacity is available.'
              : 'Intensive care capacity is constrained — see explanation.'}</small>
          </span>
        </div>
      </div>
      <p className="icu-card__explanation">{recommendation.explanation}</p>
      <footer className="icu-card__footer">
        <span>
          <Activity size={14} /> Decision Support · {new Date(recommendation.generated_at).toLocaleString()}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            type="button"
            className="button button--ghost"
            style={{ padding: '4px 10px', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            onClick={onOpenAssistant}
          >
            <MessageSquare size={14} /> Ask Assistant
          </button>
          <Link to={rolePath === 'doctor' ? `/doctor/patients/${patientId}/vitals` : `/nurse/patients/${patientId}/vitals`}>
            Open vitals
          </Link>
        </div>
      </footer>
    </article>
  )
}

/**
 * "Integration of an AI system that displays medical recommendations related
 * to the intensive care unit": surfaces the decision-support output (ICU
 * eligibility, readiness score, specialist availability, ICU bed capacity and
 * a plain-language explanation) so care does not stall when a specialist is
 * overloaded or absent.
 */
export function IcuRecommendationsView({ rolePath }: { rolePath: 'doctor' | 'nurse' }) {
  const [selectedPatient, setSelectedPatient] = useState<{ id: string; name: string } | null>(null)

  const query = useQuery({
    queryKey: ['icu-recommendations'],
    queryFn: getIcuRecommendations,
    refetchInterval: 15_000,
  })
  const recommendations = query.data?.filter((item) => item.icu_recommendation) ?? []

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Intensive care · Decision support"
        title="ICU recommendations"
        description="Automated recommendations generated from the latest critical vital-sign assessments, specialist availability and intensive-care bed capacity."
      />
      {query.isPending ? (
        <section className="section-panel">
          <SectionLoader label="Loading ICU recommendations" />
        </section>
      ) : query.error ? (
        <Alert tone="critical">ICU recommendations could not be loaded.</Alert>
      ) : recommendations.length === 0 ? (
        <section className="section-panel">
          <EmptyState
            title="No ICU recommendations yet"
            description="When a vital-sign assessment is critical, the AI system evaluates specialist availability and ICU bed capacity and shows its recommendation here."
          />
        </section>
      ) : (
        <div className="icu-recs">
          {recommendations.map((item) => (
            <RecommendationCard
              key={item.id}
              patientId={item.patient}
              patientName={item.patient_name}
              observedAt={item.observed_at}
              recommendation={item.icu_recommendation!}
              rolePath={rolePath}
              onOpenAssistant={() => setSelectedPatient({ id: item.patient, name: item.patient_name })}
            />
          ))}
        </div>
      )}
      <p className="section-hint">
        {rolePath === 'doctor'
          ? 'Recommendations refresh automatically. They support — never replace — clinical judgment.'
          : 'Recommendations refresh automatically and support the clinical team’s decisions.'}
      </p>

      {selectedPatient && (
        <ClinicalAssistantDrawer
          open={Boolean(selectedPatient)}
          onClose={() => setSelectedPatient(null)}
          patientId={selectedPatient.id}
          patientName={selectedPatient.name}
          initialPrompt="Why was this patient flagged for ICU assessment?"
        />
      )}
    </div>
  )
}

export function IcuRecommendationNotice() {
  return (
    <p className="icu-notice">
      <ShieldAlert size={15} /> Clinical decision support. Always confirm with the attending clinician.
    </p>
  )
}
