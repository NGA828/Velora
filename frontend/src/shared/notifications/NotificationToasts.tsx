import { Bell } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { subscribeRealtime } from '../realtime/bus'
import { getNotifications } from '../../modules/notifications/api'
import type { Notification } from '../../modules/notifications/types'

interface ToastItem {
  id: string
  title: string
  body: string
}

const TOAST_LIFETIME_MS = 7000
const MAX_TOASTS = 3

/**
 * Small clickable toasts shown on any page when a new notification arrives,
 * so users notice events (missed calls, assignments, alerts) without having
 * to watch the Notifications page. Hidden while the user is already reading
 * their notifications.
 */
export function NotificationToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const timers = new Map<string, number>()
    const unsubscribe = subscribeRealtime((event) => {
      if (event.type !== 'notification.created') return
      const notificationId = event.payload?.notification_id
      if (!notificationId) return
      void getNotifications()
        .then((items) => {
          const item = items.find((entry: Notification) => entry.id === notificationId)
          if (!item) return
          setToasts((current) => {
            if (current.some((toast) => toast.id === item.id)) return current
            const next = [...current, { id: item.id, title: item.title, body: item.body }]
            return next.slice(-MAX_TOASTS)
          })
          const timer = window.setTimeout(() => {
            timers.delete(item.id)
            setToasts((current) => current.filter((toast) => toast.id !== item.id))
          }, TOAST_LIFETIME_MS)
          timers.set(item.id, timer)
        })
        .catch(() => undefined)
    })
    return () => {
      unsubscribe()
      for (const timer of timers.values()) {
        window.clearTimeout(timer)
      }
      timers.clear()
    }
  }, [])

  if (toasts.length === 0 || location.pathname === '/notifications') return null

  const dismiss = (id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }

  return (
    <div className="notif-toasts" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <button
          key={toast.id}
          type="button"
          className="notif-toast"
          onClick={() => {
            dismiss(toast.id)
            navigate('/notifications')
          }}
        >
          <span className="notif-toast__icon">
            <Bell size={16} />
          </span>
          <span className="notif-toast__copy">
            <strong>{toast.title}</strong>
            <small>{toast.body}</small>
          </span>
        </button>
      ))}
    </div>
  )
}
