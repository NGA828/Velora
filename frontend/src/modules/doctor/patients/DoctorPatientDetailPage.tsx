import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, ArrowLeft, BrainCircuit, FileText, Pill, RefreshCw, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { assignNurse, getClinicalStaff, getGuardians, getPatient } from '../../patient-care/shared/api'
import { PatientOverview } from '../../patient-care/shared/PatientOverview'
import { PatientPageState } from '../../patient-care/shared/PatientPageState'
import { ClinicalAssistantDrawer } from '../../clinical-assistant/components/ClinicalAssistantDrawer'

export function DoctorPatientDetailPage() {
  const { patientId = '' } = useParams()
  const client = useQueryClient()
  const [assignOpen, setAssignOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [nurseId, setNurseId] = useState('')
  const patient = useQuery({ queryKey: ['patient', patientId], queryFn: () => getPatient(patientId), enabled: Boolean(patientId) })
  const guardians = useQuery({ queryKey: ['patient-guardians', patientId], queryFn: () => getGuardians(patientId), enabled: Boolean(patientId) })
  const nurses = useQuery({ queryKey: ['clinical-directory', 'NURSE'], queryFn: () => getClinicalStaff('NURSE') })
  const mutation = useMutation({ mutationFn: () => assignNurse(patientId, nurseId), onSuccess: async () => { setAssignOpen(false); await Promise.all([client.invalidateQueries({ queryKey: ['patient', patientId] }), client.invalidateQueries({ queryKey: ['patients'] })]) } })
  const openAssign = () => { setNurseId(patient.data?.primary_nurse?.staff_id ?? nurses.data?.[0]?.id ?? ''); setAssignOpen(true) }

  return <div className="workspace-page"><div className="back-link"><Link to="/doctor/patients"><ArrowLeft size={16} /> Back to patients</Link></div><PageHeader eyebrow="Medical record context" title={patient.data?.full_name ?? 'Patient record'} description={patient.data ? `${patient.data.medical_record_number} · Access granted through your active Doctor assignment.` : 'Loading authorized patient information.'} actions={patient.data && <><Button variant="secondary" onClick={() => setAssistantOpen(true)}><BrainCircuit size={16} /> Clinical Assistant</Button><Link className="button button--secondary" to={`/doctor/patients/${patientId}/medical-file`}><FileText size={16} /> Medical file</Link><Link className="button button--secondary" to={`/doctor/patients/${patientId}/vitals`}><Activity size={16} /> Vital history</Link><Link className="button button--secondary" to={`/doctor/patients/${patientId}/prescriptions`}><Pill size={16} /> Prescriptions</Link><Button variant="secondary" onClick={openAssign}><RefreshCw size={16} /> Reassign Nurse</Button></>} /><PatientPageState pending={patient.isPending} error={patient.error} />{patient.data && <><PatientOverview patient={patient.data} /><section className="section-panel table-panel guardian-section"><div className="section-panel__heading"><div><p className="eyebrow">Patient Guard access</p><h2>Authorized representatives</h2></div><span>Nurses create and manage Guard accounts</span></div>{guardians.isPending ? null : (guardians.data?.length ?? 0) === 0 ? <EmptyState title="No Patient Guard linked" description="The assigned Nurse can invite the patient's authorized representative." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Representative</th><th>Relationship</th><th>Medical file</th><th>Transfer decisions</th><th>Status</th></tr></thead><tbody>{guardians.data!.map((access) => <tr key={access.id}><td><strong>{access.full_name}</strong><small>{access.email}</small></td><td>{access.relationship}</td><td>{access.can_view_medical_file ? 'Authorized' : 'Restricted'}</td><td>{access.can_decide_transfers ? 'Authorized' : 'Restricted'}</td><td><StatusBadge status={access.status} /></td></tr>)}</tbody></table></div>}</section></>}
    <Modal open={assignOpen} onClose={() => setAssignOpen(false)} title="Reassign primary Nurse" description="The previous Nurse immediately loses patient access when this change succeeds."><form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}><SelectField label="New primary Nurse" required value={nurseId} onChange={(event) => setNurseId(event.target.value)}><option value="">Select active Nurse</option>{nurses.data?.map((nurse) => <option key={nurse.id} value={nurse.id}>{nurse.full_name} · {nurse.department_name || 'No department'}</option>)}</SelectField><Alert tone="information"><ShieldCheck size={16} /> Access and assignment history are updated together.</Alert>{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Reassignment failed.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setAssignOpen(false)}>Cancel</Button><Button type="submit" isLoading={mutation.isPending}>Confirm reassignment</Button></div></form></Modal>
    <ClinicalAssistantDrawer
      open={assistantOpen}
      onClose={() => setAssistantOpen(false)}
      patientId={patientId}
      patientName={patient.data?.full_name}
      medicalRecordNumber={patient.data?.medical_record_number}
    />
  </div>
}
