import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><span><Inbox /></span><h3>{title}</h3><p>{description}</p>{action}</div>
}
