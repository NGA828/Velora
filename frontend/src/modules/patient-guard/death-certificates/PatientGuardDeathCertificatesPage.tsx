import { useMutation, useQuery } from '@tanstack/react-query'
import { Printer, ScrollText } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { getDeathCertificates, getPrintableDeathCertificate } from '../../death-certificates/shared/api'
import type { DeathCertificate } from '../../death-certificates/shared/types'

export function PatientGuardDeathCertificatesPage() {
  const [printing, setPrinting] = useState<DeathCertificate | null>(null)
  const query = useQuery({ queryKey: ['death-certificates', 'guard'], queryFn: () => getDeathCertificates() })
  const printMutation = useMutation({ mutationFn: getPrintableDeathCertificate, onSuccess: (certificate) => { setPrinting(certificate); setTimeout(() => window.print(), 100) } })
  return <div className="workspace-page"><PageHeader eyebrow="Official record" title="Death certificates" description="View and print issued certificates available through your Patient Guard relationship." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Certificates could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No issued certificate available" description="An issued Doctor certificate will appear here automatically when applicable." /></section> : <div className="certificate-list">{query.data!.map((certificate) => <article key={certificate.id} className="certificate-card"><header><span><ScrollText /></span><div><h2>{certificate.patient_name}</h2><p>{certificate.certificate_number}</p></div></header><dl><div><dt>Date and time of death</dt><dd>{new Date(certificate.death_datetime).toLocaleString()}</dd></div><div><dt>Place</dt><dd>{certificate.place_of_death}</dd></div><div><dt>Primary cause</dt><dd>{certificate.primary_cause}</dd></div><div><dt>Issuing Doctor</dt><dd>{certificate.issuing_doctor_name}</dd></div></dl><footer><Button variant="secondary" isLoading={printMutation.isPending} onClick={() => printMutation.mutate(certificate.id)}><Printer size={16} /> Print certificate</Button></footer></article>)}</div>}{printMutation.error && <Alert tone="critical">The printable certificate could not be opened.</Alert>}{printing && <section className="death-certificate-print" aria-hidden="true"><header><p>Official death certificate</p><h1>{printing.certificate_number}</h1></header><dl><div><dt>Full name</dt><dd>{printing.patient_name}</dd></div><div><dt>Medical record number</dt><dd>{printing.medical_record_number}</dd></div><div><dt>Date of birth</dt><dd>{printing.date_of_birth}</dd></div><div><dt>Sex at birth</dt><dd>{printing.sex_at_birth}</dd></div><div><dt>Date and time of death</dt><dd>{new Date(printing.death_datetime).toLocaleString()}</dd></div><div><dt>Place of death</dt><dd>{printing.place_of_death}</dd></div><div><dt>Primary cause</dt><dd>{printing.primary_cause}</dd></div><div><dt>Contributing causes</dt><dd>{printing.contributing_causes || 'None recorded'}</dd></div><div><dt>Manner of death</dt><dd>{printing.manner_of_death || 'Not recorded'}</dd></div></dl><footer><p>Issued by: {printing.issuing_doctor_name}</p><p>Issued at: {printing.issued_at ? new Date(printing.issued_at).toLocaleString() : ''}</p></footer></section>}</div>
}
