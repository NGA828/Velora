import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BrainCircuit, FileText, LockKeyhole } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { ClinicalAssistantDrawer } from '../../clinical-assistant/components/ClinicalAssistantDrawer'
import { getPatient } from '../../patient-care/shared/api'
import { PatientOverview } from '../../patient-care/shared/PatientOverview'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'

export function PatientGuardPatientDetailPage() {
  const { patientId = '' } = useParams()
  const [assistantOpen, setAssistantOpen] = useState(false)
  const query = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  return (
    <div className="workspace-page">
      <div className="back-link">
        <Link to="/patient-guard/patients">
          <ArrowLeft size={16} /> Back to linked patients
        </Link>
      </div>
      <PageHeader
        eyebrow="Authorized patient record"
        title={query.data?.full_name ?? 'Patient information'}
        description={query.data ? `${query.data.medical_record_number} · Visible through your active Patient Guard relationship.` : 'Loading authorized information.'}
        actions={
          <>
            {query.data && (
              <Button variant="secondary" onClick={() => setAssistantOpen(true)}>
                <BrainCircuit size={16} /> Care Assistant
              </Button>
            )}
            {query.data?.medical_file && (
              <Link className="button button--secondary" to={`/patient-guard/patients/${patientId}/medical-file`}>
                <FileText size={16} /> Medical file
              </Link>
            )}
          </>
        }
      />
      <Alert tone="information" title="Your privacy boundary">
        <LockKeyhole size={16} /> Internal clinical notes and unapproved information are not exposed through this view.
      </Alert>
      <PatientPageState pending={query.isPending} error={query.error} />
      {query.data && <PatientOverview patient={query.data} />}
      <ClinicalAssistantDrawer
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        patientId={patientId}
        patientName={query.data?.full_name}
        medicalRecordNumber={query.data?.medical_record_number}
      />
    </div>
  )
}
