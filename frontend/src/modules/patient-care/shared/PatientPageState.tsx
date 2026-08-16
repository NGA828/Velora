import { AppApiError } from '../../../shared/api/errors'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'

export function PatientPageState({ pending, error }: { pending: boolean; error: unknown }) {
  if (pending) return <section className="section-panel"><SectionLoader label="Loading patient record" /></section>
  if (error) return <Alert tone="critical" title="Patient record unavailable">{error instanceof AppApiError ? error.message : 'Try again.'}</Alert>
  return null
}
