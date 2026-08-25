import { ShieldAlert } from 'lucide-react'

interface Props {
  isGuardian?: boolean
}

export function SafetyNotice({ isGuardian }: Props) {
  return (
    <div className="assistant-safety-notice">
      <ShieldAlert size={15} />
      <p>
        {isGuardian
          ? 'Conversational information support. Always speak directly with your attending medical team for urgent medical concerns.'
          : 'Clinical Decision Support Assistant. Recommendations support — never replace — clinical judgment by the attending team.'}
      </p>
    </div>
  )
}
