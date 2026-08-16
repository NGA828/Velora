import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, HelpCircle, MessageCircleReply } from 'lucide-react'
import { useState } from 'react'

import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { EmptyState } from '../../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { FormField } from '../../../shared/ui/forms/FormField'
import { SelectField } from '../../../shared/ui/forms/SelectField'
import { TextAreaField } from '../../../shared/ui/forms/TextAreaField'
import { PageHeader } from '../../../shared/ui/navigation/PageHeader'
import { Modal } from '../../../shared/ui/overlays/Modal'
import { answerMonitoringQuestion, getMonitoringThreads } from '../../monitoring/shared/api'
import type { MonitoringQuestion, MonitoringThread } from '../../monitoring/shared/types'

export function PatientGuardMonitoringPage() {
  const client = useQueryClient()
  const [selected, setSelected] = useState<{ thread: MonitoringThread; question: MonitoringQuestion } | null>(null)
  const [answer, setAnswer] = useState('')
  const query = useQuery({ queryKey: ['monitoring-threads', 'guard'], queryFn: () => getMonitoringThreads() })
  const mutation = useMutation({
    mutationFn: () => {
      const type = selected!.question.response_type
      const value = type === 'BOOLEAN' ? answer === 'true' : answer
      return answerMonitoringQuestion(selected!.thread.id, selected!.question.id, value)
    },
    onSuccess: async () => { setSelected(null); await Promise.all([client.invalidateQueries({ queryKey: ['monitoring-threads'] }), client.invalidateQueries({ queryKey: ['notifications'] })]) },
  })
  const open = (thread: MonitoringThread, question: MonitoringQuestion) => { mutation.reset(); setSelected({ thread, question }); const current = question.current_response?.answer; setAnswer(current === true ? 'true' : current === false ? 'false' : current == null ? '' : String(current)) }
  const pending = query.data?.reduce((count, thread) => count + thread.pending_question_count, 0) ?? 0
  return <><div className="workspace-page"><PageHeader eyebrow="Patient feedback" title="Monitoring questions" description="Respond to the Doctor’s structured questions. Previous responses remain in history when corrected." />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Monitoring questions could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No monitoring questions" description="Questions from the assigned Doctor will appear here." /></section> : <><section className="summary-strip"><div><HelpCircle /><span><small>Awaiting response</small><strong>{pending}</strong></span></div><div><CheckCircle2 /><span><small>Monitoring threads</small><strong>{query.data?.length ?? 0}</strong></span></div></section><div className="monitoring-list">{query.data!.map((thread) => <article key={thread.id} className="monitoring-thread"><header><div><span className="monitoring-thread__icon"><MessageCircleReply /></span><div><h2>{thread.subject}</h2><p>{thread.patient_name} · Dr. {thread.doctor_name}</p></div></div><StatusBadge status={thread.status} /></header><div className="question-list">{thread.questions.map((question) => <section key={question.id}><div className="question-prompt"><span>{question.sequence}</span><div><strong>{question.prompt}</strong><small>{question.response_type_label}{question.due_at ? ` · Due ${new Date(question.due_at).toLocaleString()}` : ''}</small></div></div>{question.current_response ? <div className="monitoring-answer"><strong>{String(question.current_response.answer)}</strong><small>Submitted {new Date(question.current_response.submitted_at).toLocaleString()}</small>{question.responses.length > 1 && <span>Correction history preserved</span>}</div> : <div className="awaiting-answer">Response requested</div>}{thread.status === 'OPEN' && <Button variant={question.current_response ? 'ghost' : 'primary'} onClick={() => open(thread, question)}>{question.current_response ? 'Correct response' : 'Answer question'}</Button>}</section>)}</div></article>)}</div></>}</div>
    <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title="Submit monitoring response" description={selected?.question.prompt}><form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>{selected?.question.response_type === 'BOOLEAN' ? <SelectField label="Response" required value={answer} onChange={(e) => setAnswer(e.target.value)}><option value="">Select Yes or No</option><option value="true">Yes</option><option value="false">No</option></SelectField> : selected?.question.response_type === 'SINGLE_CHOICE' ? <SelectField label="Response" required value={answer} onChange={(e) => setAnswer(e.target.value)}><option value="">Select response</option>{selected.question.options.map((option) => <option key={option} value={option}>{option}</option>)}</SelectField> : selected?.question.response_type === 'NUMBER' ? <FormField label="Numeric response" type="number" step="any" required value={answer} onChange={(e) => setAnswer(e.target.value)} /> : <TextAreaField label="Response" required rows={4} value={answer} onChange={(e) => setAnswer(e.target.value)} />}{selected?.question.current_response && <Alert tone="information">Submitting a correction preserves the previous response in history.</Alert>}{mutation.error && <Alert tone="critical">{mutation.error instanceof AppApiError ? mutation.error.message : 'Response could not be submitted.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setSelected(null)}>Cancel</Button><Button type="submit" disabled={!answer} isLoading={mutation.isPending}>Submit response</Button></div></form></Modal>
  </>
}
