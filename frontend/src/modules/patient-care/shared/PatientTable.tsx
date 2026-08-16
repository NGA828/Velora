import { Link } from 'react-router-dom'

import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import type { Patient } from './types'

export function PatientTable({ patients, linkFor, emptyAction }: { patients: Patient[]; linkFor: (patient: Patient) => string; emptyAction?: React.ReactNode }) {
  if (patients.length === 0) return <EmptyState title="No patients in this workspace" description="Patients appear only after an authorized care or Patient Guard relationship is created." action={emptyAction} />
  return <div className="table-scroll"><table className="data-table"><thead><tr><th>Patient</th><th>Care status</th><th>Latest vitals</th><th>Department</th><th>Primary Nurse</th><th>Patient Guards</th><th /></tr></thead><tbody>{patients.map((patient) => <tr key={patient.id}><td><strong>{patient.full_name}</strong><small>{patient.medical_record_number} · {patient.age} years</small></td><td><StatusBadge status={patient.status} /></td><td>{patient.latest_vital_status ? <><StatusBadge status={patient.latest_vital_status} /><small>{patient.latest_vital_at ? new Date(patient.latest_vital_at).toLocaleString() : ''}</small></> : <span className="muted-copy">Not recorded</span>}</td><td>{patient.current_department?.name ?? 'Not assigned'}</td><td>{patient.primary_nurse?.name ?? 'Not assigned'}</td><td>{patient.active_guardian_count}</td><td><Link className="table-link" to={linkFor(patient)}>Open record</Link></td></tr>)}</tbody></table></div>
}
