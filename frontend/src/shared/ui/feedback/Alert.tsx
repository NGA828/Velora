import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info } from 'lucide-react'

interface AlertProps {
  children: ReactNode
  title?: string
  tone?: 'critical' | 'success' | 'information'
}

const icons = {
  critical: AlertCircle,
  success: CheckCircle2,
  information: Info,
}

export function Alert({ children, title, tone = 'information' }: AlertProps) {
  const Icon = icons[tone]
  return (
    <div className={`alert alert--${tone}`} role={tone === 'critical' ? 'alert' : 'status'}>
      <Icon size={20} aria-hidden="true" />
      <div>
        {title && <strong>{title}</strong>}
        <div>{children}</div>
      </div>
    </div>
  )
}
