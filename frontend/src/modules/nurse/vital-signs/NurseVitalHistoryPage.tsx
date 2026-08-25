import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BrainCircuit, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '../../../shared/ui/actions/Button'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { ClinicalAssistantDrawer } from '../../clinical-assistant/components/ClinicalAssistantDrawer'
import { getPatient } from '../../patient-care/shared/api'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { VitalHistory } from '../../vital-signs/shared/VitalHistory'

export function NurseVitalHistoryPage() {
  const { patientId = '' } = useParams()
  const [assistantOpen, setAssistantOpen] = useState(false)
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return (
    <div className="workspace-page">
      <div className="back-link">
        <Link to={`/nurse/patients/${patientId}`}>
          <ArrowLeft size={16} /> Back to patient overview
        </Link>
      </div>
      <PageHeader
        eyebrow="Patient monitoring"
        title={patient.data ? `${patient.data.full_name} · Vital history` : 'Vital history'}
        description="Measurements, stability or criticality percentage, and the configured explanations used at the time."
        actions={
          <>
            {patient.data && (
              <Button variant="secondary" onClick={() => setAssistantOpen(true)}>
                <BrainCircuit size={16} /> Ask Assistant
              </Button>
            )}
            <Link className="button button--primary" to={`/nurse/patients/${patientId}/vitals/new`}>
              <Plus size={16} /> Record vitals
            </Link>
          </>
        }
      />
      <PatientPageState pending={patient.isPending} error={patient.error} />
      {patient.data && <VitalHistory patientId={patientId} />}
      <ClinicalAssistantDrawer
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        patientId={patientId}
        patientName={patient.data?.full_name}
        medicalRecordNumber={patient.data?.medical_record_number}
      />
    </div>
  )
}
