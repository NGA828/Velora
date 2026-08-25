import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '../../shared/ui/actions/Button'
import { StatusBadge } from '../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../shared/ui/feedback/Alert'
import { EmptyState } from '../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../shared/ui/feedback/SectionLoader'
import { PageHeader } from '../../shared/ui/navigation/PageHeader'
import { getNotifications, markAllNotificationsRead, markNotificationRead } from './api'

export function NotificationsPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['notifications'], queryFn: () => getNotifications() })
  const refresh = () => {
    void client.invalidateQueries({ queryKey: ['notifications'] })
    void client.invalidateQueries({ queryKey: ['notifications', 'unread'] })
  }
  const readMutation = useMutation({ mutationFn: markNotificationRead, onSuccess: refresh })
  const allMutation = useMutation({ mutationFn: markAllNotificationsRead, onSuccess: refresh })
  const unread = query.data?.filter((item) => !item.read_at).length ?? 0
  return <div className="workspace-page workspace-page--narrow"><PageHeader eyebrow="Activity center" title="Notifications" description="Persistent care and access events assigned to your account." actions={unread > 0 && <Button variant="secondary" isLoading={allMutation.isPending} onClick={() => allMutation.mutate()}><CheckCheck size={16} /> Mark all read</Button>} />{query.isPending ? <SectionLoader /> : query.error ? <Alert tone="critical">Notifications could not be loaded.</Alert> : (query.data?.length ?? 0) === 0 ? <section className="section-panel"><EmptyState title="No notifications" description="Patient assignments, critical alerts and workflow updates will appear here." /></section> : <section className="notification-list">{query.data!.map((item) => <article key={item.id} className={!item.read_at ? 'notification-item notification-item--unread' : 'notification-item'}><span className={`notification-item__icon notification-item__icon--${item.severity.toLowerCase()}`}><Bell /></span><div><div className="notification-item__heading"><strong>{item.title}</strong><StatusBadge status={item.severity} /></div><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString()}{item.actor_name ? ` · ${item.actor_name}` : ''}</small><div className="notification-item__actions">{item.route && <Link to={item.route} onClick={() => !item.read_at && readMutation.mutate(item.id)}>Open</Link>}{!item.read_at && <button onClick={() => readMutation.mutate(item.id)}>Mark read</button>}</div></div></article>)}</section>}</div>
}
