import { useQuery } from '@tanstack/react-query'
import { BrainCircuit, HeartPulse, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { ClinicalAssistantPanel } from '../../clinical-assistant/components/ClinicalAssistantPanel'
import { getPatients } from '../../patient-care/shared/api'

/**
 * Sidebar entry for Patient Guards: a dedicated conversation workspace where
 * the guardian can ask the Clinical Assistant about the patients they are
 * authorized to follow.
 */
export function PatientGuardAssistantPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Clinical Assistant · Velora'
  }, [])

  const patientsQuery = useQuery({
    queryKey: ['guard-assistant-patients'],
    queryFn: () => getPatients(),
  })

  const patients = patientsQuery.data || []
  const selected = patients.find((patient) => patient.id === selectedId) || patients[0] || null

  if (patientsQuery.isPending) {
    return (
      <div className="workspace-page">
        <PageHeader
          eyebrow="Authorized care information"
          title="Clinical Assistant"
          description="Ask plain-language questions about the care of patients linked to your Patient Guard access."
        />
        <SectionLoader label="Loading your linked patients..." />
      </div>
    )
  }

  if (patientsQuery.isError) {
    return (
      <div className="workspace-page">
        <PageHeader
          eyebrow="Authorized care information"
          title="Clinical Assistant"
          description="Ask plain-language questions about the care of patients linked to your Patient Guard access."
        />
        <Alert tone="critical" title="We could not load your linked patients">
          {patientsQuery.error instanceof Error ? patientsQuery.error.message : 'Please try again.'}
        </Alert>
      </div>
    )
  }

  return (
    <div className="workspace-page">
      <PageHeader
        eyebrow="Authorized care information"
        title="Clinical Assistant"
        description="Ask plain-language questions about the care of patients linked to your Patient Guard access. The assistant only explains information you are authorized to see."
        actions={
          <span className="status-pill status-pill--success">
            <ShieldCheck size={15} /> Privacy boundary enforced
          </span>
        }
      />

      {patients.length === 0 ? (
        <Alert tone="information" title="No linked patients yet">
          <HeartPulse size={16} /> Once a nurse links your Patient Guard access to a patient, you
          will be able to ask the assistant about their care here.
        </Alert>
      ) : (
        <>
          {patients.length > 1 && (
            <div className="assistant-patient-picker" role="tablist" aria-label="Choose a patient">
              {patients.map((patient) => {
                const isActive = selected?.id === patient.id
                return (
                  <button
                    key={patient.id}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    className={`assistant-patient-chip ${isActive ? 'assistant-patient-chip--active' : ''}`}
                    onClick={() => setSelectedId(patient.id)}
                  >
                    <BrainCircuit size={14} />
                    <span>{patient.full_name}</span>
                    <small>{patient.medical_record_number}</small>
                  </button>
                )
              })}
            </div>
          )}

          {selected && (
            <ClinicalAssistantPanel
              key={selected.id}
              patientId={selected.id}
              patientName={selected.full_name}
              medicalRecordNumber={selected.medical_record_number}
            />
          )}
        </>
      )}
    </div>
  )
}
