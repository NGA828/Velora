import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Mic, MicOff, Phone, PhoneCall, PhoneOff } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { useSession } from '../auth/hooks/use-session'
import { AppApiError } from '../../shared/api/errors'
import { Button } from '../../shared/ui/actions/Button'
import { StatusBadge } from '../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../shared/ui/feedback/Alert'
import { EmptyState } from '../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../shared/ui/feedback/SectionLoader'
import { SelectField } from '../../shared/ui/forms/SelectField'
import { PageHeader } from '../../shared/ui/navigation/PageHeader'
import { useRealtimeEvent } from '../../shared/realtime/bus'
import {
  createCall,
  getCallAvailability,
  getCalls,
  getEligibleContacts,
  signalCall,
  updateCallStatus,
} from '../communication/shared/api'
import type { CallSession } from '../communication/shared/types'

const ICE_CONFIGURATION: RTCConfiguration = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
}

const TERMINAL_STATUSES = ['COMPLETED', 'DECLINED', 'CANCELLED', 'FAILED', 'NO_ANSWER']

type SignalData =
  | { type: 'offer'; sdp: string }
  | { type: 'answer'; sdp: string }
  | { type: 'candidate'; candidate: RTCIceCandidateInit }
  | { type: 'bye' }

type CallPhase = 'idle' | 'ringing' | 'incoming' | 'connecting' | 'active' | 'ended'

function peerId(session: CallSession, userId: string): string | undefined {
  return session.participants.find((participant) => participant.user_id !== userId)?.user_id
}

function peerName(session: CallSession, userId: string): string {
  return (
    session.participants.find((participant) => participant.user_id !== userId)?.full_name ??
    'Participant'
  )
}

async function flushCandidates(pc: RTCPeerConnection, pending: RTCIceCandidateInit[]): Promise<void> {
  const buffered = pending.splice(0, pending.length)
  for (const candidate of buffered) {
    try {
      await pc.addIceCandidate(new RTCIceCandidate(candidate))
    } catch {
      // Late or redundant candidates are safe to ignore.
    }
  }
}

export function CallsPage() {
  const { data: session } = useSession()
  const user = session!.user
  const client = useQueryClient()

  const availability = useQuery({ queryKey: ['call-availability'], queryFn: getCallAvailability })
  const contacts = useQuery({ queryKey: ['eligible-contacts'], queryFn: getEligibleContacts })
  const calls = useQuery({ queryKey: ['calls'], queryFn: getCalls, refetchInterval: 20_000 })

  const [recipient, setRecipient] = useState('')
  const [activeSession, setActiveSession] = useState<CallSession | null>(null)
  const [role, setRole] = useState<'caller' | 'callee' | null>(null)
  const [phase, setPhase] = useState<CallPhase>('idle')
  const [error, setError] = useState('')
  const [muted, setMuted] = useState(false)
  const [starting, setStarting] = useState(false)

  const pcRef = useRef<RTCPeerConnection | null>(null)
  const localStreamRef = useRef<MediaStream | null>(null)
  const pendingCandidatesRef = useRef<RTCIceCandidateInit[]>([])
  const offersRef = useRef<Record<string, { fromUser: string; sdp: string }>>({})
  const localAudioRef = useRef<HTMLAudioElement | null>(null)
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null)
  const activeSessionIdRef = useRef<string | null>(null)

  const activeSessionRef = useRef<CallSession | null>(null)
  activeSessionRef.current = activeSession
  const userIdRef = useRef(user.id)
  userIdRef.current = user.id

  const closePeer = useCallback(() => {
    const pc = pcRef.current
    if (pc) {
      pc.ontrack = null
      pc.onicecandidate = null
      pc.onconnectionstatechange = null
      try {
        pc.close()
      } catch {
        // already closed
      }
      pcRef.current = null
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop())
      localStreamRef.current = null
    }
    pendingCandidatesRef.current = []
  }, [])

  const resetToIdle = useCallback(() => {
    window.setTimeout(() => {
      setActiveSession(null)
      setRole(null)
      activeSessionIdRef.current = null
      setPhase('idle')
    }, 1500)
  }, [])

  const sendSignal = useCallback(async (data: SignalData) => {
    const current = activeSessionRef.current
    if (!current) return
    const other = peerId(current, userIdRef.current)
    if (!other) return
    try {
      await signalCall(current.id, other, data)
    } catch {
      // Transient signaling errors must not crash the call UI.
    }
  }, [])

  const makePeerConnection = useCallback((): RTCPeerConnection => {
    const pc = new RTCPeerConnection(ICE_CONFIGURATION)
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        void sendSignal({ type: 'candidate', candidate: event.candidate.toJSON() })
      }
    }
    pc.ontrack = (event) => {
      const audio = remoteAudioRef.current
      if (audio && event.streams[0]) {
        audio.srcObject = event.streams[0]
      }
    }
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'connected' && activeSessionIdRef.current) {
        setPhase('active')
        void updateCallStatus(activeSessionIdRef.current, 'IN_PROGRESS').catch(() => undefined)
      }
      if (pc.connectionState === 'failed') {
        setError('The connection dropped. Please try the call again.')
        closePeer()
        setPhase('ended')
        resetToIdle()
      }
    }
    pcRef.current = pc
    return pc
  }, [sendSignal])

  const startMedia = useCallback(async (): Promise<MediaStream> => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    localStreamRef.current = stream
    if (localAudioRef.current) {
      localAudioRef.current.srcObject = stream
    }
    return stream
  }, [])

  const endActiveCall = useCallback(async () => {
    await sendSignal({ type: 'bye' })
    const current = activeSessionRef.current
    if (current) {
      await updateCallStatus(current.id, 'COMPLETED').catch(() => undefined)
    }
    closePeer()
    setPhase('ended')
    resetToIdle()
  }, [sendSignal, closePeer, resetToIdle])

  const startCall = useCallback(async () => {
    if (!recipient || starting) return
    setError('')
    setStarting(true)
    let created: CallSession
    try {
      created = await createCall(recipient, null, 'WEBRTC')
    } catch (exception) {
      setError(exception instanceof AppApiError ? exception.message : 'Could not start the call.')
      setStarting(false)
      return
    }
    activeSessionIdRef.current = created.id
    setActiveSession(created)
    setRole('caller')
    setPhase('ringing')
    try {
      const stream = await startMedia()
      const pc = makePeerConnection()
      stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      await sendSignal({ type: 'offer', sdp: offer.sdp ?? '' })
      await updateCallStatus(created.id, 'RINGING')
    } catch {
      setError('Microphone access is required to place a call.')
      await updateCallStatus(created.id, 'FAILED').catch(() => undefined)
      closePeer()
      setPhase('ended')
      resetToIdle()
    } finally {
      setStarting(false)
    }
  }, [recipient, starting, createCall, startMedia, makePeerConnection, sendSignal, closePeer, resetToIdle])

  const acceptCall = useCallback(
    async (incoming: CallSession) => {
      setError('')
      const offer = offersRef.current[incoming.id]
      if (!offer) {
        setError('The call invitation expired. Ask the caller to try again.')
        return
      }
      activeSessionIdRef.current = incoming.id
      setActiveSession(incoming)
      setRole('callee')
      setPhase('connecting')
      try {
        const stream = await startMedia()
        const pc = makePeerConnection()
        stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
        await pc.setRemoteDescription({ type: 'offer', sdp: offer.sdp })
        await flushCandidates(pc, pendingCandidatesRef.current)
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await sendSignal({ type: 'answer', sdp: answer.sdp ?? '' })
        await updateCallStatus(incoming.id, 'IN_PROGRESS')
      } catch {
        setError('Could not answer the call. Please try again.')
        await updateCallStatus(incoming.id, 'FAILED').catch(() => undefined)
        closePeer()
        setPhase('ended')
        resetToIdle()
      }
    },
    [startMedia, makePeerConnection, sendSignal, closePeer, resetToIdle],
  )

  const declineCall = useCallback(
    async (incoming: CallSession) => {
      const other = peerId(incoming, user.id)
      if (other) {
        try {
          await signalCall(incoming.id, other, { type: 'bye' } satisfies SignalData)
        } catch {
          // best-effort notification
        }
      }
      try {
        await updateCallStatus(incoming.id, 'DECLINED')
      } catch {
        // ignore
      }
      void client.invalidateQueries({ queryKey: ['calls'] })
    },
    [user.id, client],
  )

  const toggleMute = useCallback(() => {
    const next = !muted
    setMuted(next)
    if (localStreamRef.current) {
      localStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = !next
      })
    }
  }, [muted])

  // React to signaling events relayed through the realtime event bus.
  useRealtimeEvent((event) => {
    if (event.type !== 'call.signal') return
    const sessionId = event.payload?.call_session_id
    const data = event.payload?.data as SignalData | undefined
    if (!sessionId || !data) return
    if (data.type === 'offer') {
      offersRef.current[sessionId] = { fromUser: event.payload?.from_user ?? '', sdp: data.sdp }
      return
    }
    if (data.type === 'answer') {
      const pc = pcRef.current
      if (sessionId === activeSessionIdRef.current && pc) {
        void pc.setRemoteDescription({ type: 'answer', sdp: data.sdp }).then(() =>
          flushCandidates(pc, pendingCandidatesRef.current),
        )
      }
      return
    }
    if (data.type === 'candidate') {
      const pc = pcRef.current
      if (pc && pc.remoteDescription) {
        void pc.addIceCandidate(new RTCIceCandidate(data.candidate)).catch(() => undefined)
      } else {
        pendingCandidatesRef.current.push(data.candidate)
      }
      return
    }
    if (data.type === 'bye') {
      closePeer()
      setPhase('ended')
      resetToIdle()
    }
  })

  // Reflect server-driven terminal states (e.g. the other party declined).
  useEffect(() => {
    const current = calls.data?.find((item) => item.id === activeSessionIdRef.current)
    if (current && TERMINAL_STATUSES.includes(current.status) && phase !== 'ended') {
      closePeer()
      setPhase('ended')
      resetToIdle()
    }
  }, [calls.data, phase, closePeer, resetToIdle])

  useEffect(() => () => closePeer(), [closePeer])

  const incoming = calls.data?.find(
    (item) =>
      item.initiated_by !== user.id &&
      !TERMINAL_STATUSES.includes(item.status) &&
      item.id !== activeSessionIdRef.current,
  )

  const phaseLabel: Record<CallPhase, string> = {
    idle: '',
    ringing: 'Ringing…',
    incoming: 'Incoming call',
    connecting: 'Connecting…',
    active: 'Call in progress',
    ended: 'Call ended',
  }

  return (
    <div className="workspace-page workspace-page--narrow">
      <PageHeader
        eyebrow="Voice communication"
        title="Calls"
        description="In-app secure voice calls between authorized hospital contacts. Media stays in the browser; Velora records call state, not audio."
      />
      {availability.isPending ? (
        <SectionLoader />
      ) : (
        <section className="section-panel call-control">
          <div>
            <span className="call-control__icon">
              <PhoneCall />
            </span>
            <div>
              <h2>Start a secure voice call</h2>
              <p>Select an authorized contact. Your browser handles the audio; Velora stores call state.</p>
            </div>
          </div>
          <SelectField
            label="Contact"
            value={recipient}
            onChange={(event) => setRecipient(event.target.value)}
          >
            <option value="">Select authorized contact</option>
            {contacts.data?.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.full_name} · {contact.role_label}
              </option>
            ))}
          </SelectField>
          <Button
            disabled={!recipient || Boolean(activeSession) || starting}
            isLoading={starting}
            onClick={() => void startCall()}
          >
            <Phone size={16} /> Start call
          </Button>
        </section>
      )}
      {error && <Alert tone="critical">{error}</Alert>}
      {incoming && !activeSession && (
        <section className="incoming-call">
          <div>
            <span className="call-pulse">
              <Phone />
            </span>
            <div>
              <strong>Incoming call from {peerName(incoming, user.id)}</strong>
              <small>In-app secure voice</small>
            </div>
          </div>
          <Button onClick={() => void acceptCall(incoming)}>
            <Phone size={16} /> Accept
          </Button>
          <Button variant="danger" onClick={() => void declineCall(incoming)}>
            <PhoneOff size={16} /> Decline
          </Button>
        </section>
      )}
      {activeSession && (
        <section className="active-call">
          <span className="call-pulse">
            <PhoneCall />
          </span>
          <div>
            <strong>{phaseLabel[phase] || 'Call'}</strong>
            <small>
              {peerName(activeSession, user.id)} · {role === 'caller' ? 'Outgoing' : 'Incoming'}
            </small>
          </div>
          {/* Local (muted) keeps the captured track alive; remote is audible. */}
          <audio ref={localAudioRef} muted autoPlay playsInline />
          <audio ref={remoteAudioRef} autoPlay playsInline />
          {phase === 'active' && (
            <Button variant="secondary" onClick={toggleMute} aria-label={muted ? 'Unmute' : 'Mute'}>
              {muted ? <MicOff size={16} /> : <Mic size={16} />}
              {muted ? 'Unmute' : 'Mute'}
            </Button>
          )}
          {phase !== 'ended' && (
            <Button variant="danger" onClick={() => void endActiveCall()}>
              <PhoneOff size={16} /> End call
            </Button>
          )}
        </section>
      )}
      <section className="section-panel table-panel">
        <div className="section-panel__heading">
          <div>
            <p className="eyebrow">Call records</p>
            <h2>History</h2>
          </div>
        </div>
        {calls.isPending ? (
          <SectionLoader />
        ) : (calls.data?.length ?? 0) === 0 ? (
          <EmptyState title="No calls recorded" description="Secure in-app call sessions will appear here." />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Participants</th>
                  <th>Initiated</th>
                  <th>Answered</th>
                  <th>Ended</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {calls.data!.map((call) => (
                  <tr key={call.id}>
                    <td>
                      <strong>{call.participants.map((item) => item.full_name).join(' ↔ ')}</strong>
                      <small>{call.patient_name || 'No patient context'}</small>
                    </td>
                    <td>{new Date(call.initiated_at).toLocaleString()}</td>
                    <td>{call.answered_at ? new Date(call.answered_at).toLocaleTimeString() : '—'}</td>
                    <td>{call.ended_at ? new Date(call.ended_at).toLocaleTimeString() : '—'}</td>
                    <td>
                      <StatusBadge status={call.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
