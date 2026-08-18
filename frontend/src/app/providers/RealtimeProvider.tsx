import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { publishRealtimeEvent, type RealtimeEvent } from '../../shared/realtime/bus'

export function RealtimeProvider({ userId }: { userId: string }) {
  const client = useQueryClient()

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined
    let attempts = 0
    let closed = false

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/events/`)
      socket.onopen = () => { attempts = 0 }
      socket.onmessage = (message) => {
        let event: RealtimeEvent
        try {
          event = JSON.parse(message.data) as RealtimeEvent
        } catch {
          return
        }
        // Side-effect refreshes keep existing list/detail views fresh.
        if (event.type.startsWith('message.')) {
          void client.invalidateQueries({ queryKey: ['conversations'] })
          if (event.payload?.conversation_id) {
            void client.invalidateQueries({ queryKey: ['messages', event.payload.conversation_id] })
          }
        }
        if (event.type.startsWith('notification.')) {
          void client.invalidateQueries({ queryKey: ['notifications'] })
        }
        if (event.type.startsWith('call.')) {
          void client.invalidateQueries({ queryKey: ['calls'] })
        }
        // Broadcast to components that need the raw payload (e.g. WebRTC signaling).
        publishRealtimeEvent(event)
      }
      socket.onclose = () => {
        if (closed) return
        attempts += 1
        reconnectTimer = window.setTimeout(connect, Math.min(30_000, 1_000 * 2 ** attempts))
      }
    }

    connect()
    return () => {
      closed = true
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [client, userId])

  return null
}
