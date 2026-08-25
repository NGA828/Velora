import { useEffect, useRef } from 'react'

export interface RealtimeEvent {
  type: string
  payload?: {
    conversation_id?: string
    call_session_id?: string
    notification_id?: string
    from_user?: string
    initiated_by?: string
    status?: string
    data?: unknown
  }
}

type Listener = (event: RealtimeEvent) => void

const listeners = new Set<Listener>()

export function publishRealtimeEvent(event: RealtimeEvent): void {
  for (const listener of listeners) {
    try {
      listener(event)
    } catch (error) {
      // A misbehaving listener must not break the WebSocket loop.
      console.error('Realtime listener threw', error)
    }
  }
}

export function subscribeRealtime(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Subscribe to realtime server events for the lifetime of the component. */
export function useRealtimeEvent(handler: (event: RealtimeEvent) => void): void {
  const handlerRef = useRef(handler)
  handlerRef.current = handler
  useEffect(() => subscribeRealtime((event) => handlerRef.current(event)), [])
}
