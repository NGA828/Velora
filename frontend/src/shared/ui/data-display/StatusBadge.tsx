interface StatusBadgeProps {
  status: string
  label?: string
}

const toneByStatus: Record<string, string> = {
  ACTIVE: 'success', AVAILABLE: 'success', ACCEPTED: 'success', ADMITTED: 'success', STABLE: 'success', APPROVED: 'success', ISSUED: 'success', FILE_SENT: 'success', PAID: 'success', POSTED: 'success',
  REGISTERED: 'information', INFORMATION: 'information', INVITED: 'warning', UNASSESSED: 'warning', RECOMMENDED: 'information',
  DRAFT: 'neutral', PENDING: 'warning', PENDING_GUARDIAN: 'warning', PARTIALLY_PAID: 'warning', QUEUED: 'warning', WARNING: 'warning', LIMITED: 'warning', MAINTENANCE: 'warning', SUCCESS: 'success',
  RINGING: 'information', IN_PROGRESS: 'success',
  INACTIVE: 'neutral', RETIRED: 'neutral', CLOSED: 'neutral', DISCHARGED: 'neutral', ARCHIVED: 'neutral', COMPLETED: 'neutral', CANCELLED: 'neutral',
  UNAVAILABLE: 'critical', REVOKED: 'critical', REVERSED: 'critical', EXPIRED: 'critical', DECEASED: 'critical', CRITICAL: 'critical', REJECTED: 'critical', VOID: 'critical', DECLINED: 'critical', FAILED: 'critical', NO_ANSWER: 'warning',
  TRANSFERRED: 'information',
  OCCUPIED: 'information', ON_LEAVE: 'information',
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const tone = toneByStatus[status] ?? 'neutral'
  const text = label ?? status.replaceAll('_', ' ').toLowerCase().replace(/^./, (char) => char.toUpperCase())
  return <span className={`status-badge status-badge--${tone}`}>{text}</span>
}
