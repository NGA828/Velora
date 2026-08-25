import { useSyncExternalStore } from 'react'

import {
  createCall,
  getCall,
  getCalls,
  getIceConfig,
  signalCall,
  updateCallStatus,
} from '../../modules/communication/shared/api'
import type { CallSession } from '../../modules/communication/shared/types'
import { AppApiError } from '../api/errors'
import type { RealtimeEvent } from '../realtime/bus'
import { startRingtone, stopRingtone } from './ringtone'

const DEFAULT_ICE_SERVERS: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }]

function candidateKey(candidate: RTCIceCandidateInit | null | undefined): string {
  if (!candidate) return ''
  return `${candidate.candidate ?? ''}|${candidate.sdpMid ?? ''}|${candidate.sdpMLineIndex ?? ''}`
}

const TERMINAL_STATUSES = ['COMPLETED', 'DECLINED', 'CANCELLED', 'FAILED', 'NO_ANSWER']

/** How long the callee's phone rings before the call counts as missed. */
export const RING_TIMEOUT_MS = 30_000

const NOTICE_BY_STATUS: Record<string, string> = {
  DECLINED: 'The call was declined.',
  CANCELLED: 'The call was cancelled.',
  FAILED: 'The call could not be connected.',
  NO_ANSWER: 'The call was not answered.',
}

type SignalData =
  | { type: 'offer'; sdp: string }
  | { type: 'answer'; sdp: string }
  | { type: 'candidate'; candidate: RTCIceCandidateInit }
  | { type: 'bye' }
  | { type: 'request_offer' }

export type CallPhase = 'idle' | 'ringing' | 'incoming' | 'connecting' | 'active' | 'ended'

export interface CallState {
  phase: CallPhase
  role: 'caller' | 'callee' | null
  activeSession: CallSession | null
  incomingSession: CallSession | null
  error: string
  notice: string
  muted: boolean
  starting: boolean
  accepting: boolean
}

const INITIAL_STATE: CallState = {
  phase: 'idle',
  role: null,
  activeSession: null,
  incomingSession: null,
  error: '',
  notice: '',
  muted: false,
  starting: false,
  accepting: false,
}

export function peerId(session: CallSession, userId: string): string | undefined {
  return session.participants.find((participant) => participant.user_id !== userId)?.user_id
}

export function peerName(session: CallSession, userId: string): string {
  return (
    session.participants.find((participant) => participant.user_id !== userId)?.full_name ??
    'Participant'
  )
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

class CallManager {
  private listeners = new Set<() => void>()
  private state: CallState = INITIAL_STATE

  private userId: string | null = null
  private pc: RTCPeerConnection | null = null
  private localStream: MediaStream | null = null
  private localAudio: HTMLAudioElement | null = null
  private remoteAudio: HTMLAudioElement | null = null

  /** SDP offers received over the realtime bus, keyed by call session id. */
  private offers = new Map<string, { fromUser: string; sdp: string }>()
  /** ICE candidates that arrived before the remote description, per session. */
  private pendingCandidates = new Map<string, RTCIceCandidateInit[]>()
  /** ICE candidates already applied to a peer connection, per session. */
  private appliedCandidates = new Map<string, Set<string>>()
  private iceConfiguration: RTCConfiguration | null = null
  private iceConfigPromise: Promise<RTCConfiguration> | null = null
  private activeSessionId: string | null = null
  private pollTimer: number | null = null
  private noticeTimer: number | null = null
  private ringTimer: number | null = null
  private starting = false
  private accepting = false

  // ---------------------------------------------------------------------------
  // Store plumbing
  // ---------------------------------------------------------------------------

  getSnapshot = (): CallState => this.state

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  private setState(patch: Partial<CallState>): void {
    this.state = { ...this.state, ...patch }
    for (const listener of this.listeners) {
      try {
        listener()
      } catch {
        // A misbehaving listener must not break call handling.
      }
    }
  }

  /** Bind the authenticated user once (idempotent). */
  configure(userId: string): void {
    if (this.userId === userId) return
    this.userId = userId
    // A call that was already ringing when the app loaded should surface
    // immediately, without waiting for a realtime event.
    void this.pollForIncoming()
  }

  startPolling(): void {
    if (this.pollTimer !== null) return
    void this.pollForIncoming()
    this.pollTimer = window.setInterval(() => void this.pollForIncoming(), 10_000)
  }

  stopPolling(): void {
    if (this.pollTimer !== null) {
      window.clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  }

  setAudioElements(local: HTMLAudioElement | null, remote: HTMLAudioElement | null): void {
    this.localAudio = local
    this.remoteAudio = remote
  }

  /** Full teardown for logout/unmount. */
  dispose(): void {
    this.stopPolling()
    this.clearRingTimer()
    this.closePeer()
    stopRingtone()
    this.userId = null
    this.activeSessionId = null
    this.offers.clear()
    this.pendingCandidates.clear()
    this.appliedCandidates.clear()
    this.iceConfiguration = null
    this.iceConfigPromise = null
    this.starting = false
    this.accepting = false
    this.setState({ ...INITIAL_STATE })
  }

  private clearRingTimer(): void {
    if (this.ringTimer !== null) {
      window.clearTimeout(this.ringTimer)
      this.ringTimer = null
    }
  }

  /**
   * WhatsApp-style ring timeout: after RING_TIMEOUT_MS the unanswered call is
   * marked NO_ANSWER (which the server records as a missed-call notification).
   */
  private scheduleRingTimeout(sessionId: string): void {
    this.clearRingTimer()
    this.ringTimer = window.setTimeout(() => {
      this.ringTimer = null
      if (this.state.incomingSession?.id !== sessionId) return
      stopRingtone()
      this.setState({ incomingSession: null, notice: 'Missed call' })
      void updateCallStatus(sessionId, 'NO_ANSWER').catch(() => undefined)
      if (this.noticeTimer !== null) window.clearTimeout(this.noticeTimer)
      this.noticeTimer = window.setTimeout(() => {
        this.setState({ notice: '' })
        this.noticeTimer = null
      }, 4500)
    }, RING_TIMEOUT_MS)
  }

  // ---------------------------------------------------------------------------
  // WebRTC plumbing
  // ---------------------------------------------------------------------------

  private closePeer(): void {
    const pc = this.pc
    if (pc) {
      pc.ontrack = null
      pc.onicecandidate = null
      pc.onconnectionstatechange = null
      try {
        pc.close()
      } catch {
        // already closed
      }
      this.pc = null
    }
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => track.stop())
      this.localStream = null
    }
    this.pendingCandidates.clear()
    this.appliedCandidates.clear()
  }

  private async startMedia(): Promise<MediaStream> {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.localStream = stream
    if (this.localAudio) {
      this.localAudio.srcObject = stream
    }
    return stream
  }

  private async getIceConfiguration(): Promise<RTCConfiguration> {
    if (this.iceConfiguration) return this.iceConfiguration
    if (!this.iceConfigPromise) {
      this.iceConfigPromise = getIceConfig()
        .then((config) => {
          const iceServers = config.iceServers?.length ? config.iceServers : DEFAULT_ICE_SERVERS
          this.iceConfiguration = { iceServers }
          return this.iceConfiguration
        })
        .catch(() => {
          // STUN-only is a best-effort fallback; deployments needing reliable
          // cross-network calls should configure TURN in the environment.
          this.iceConfiguration = { iceServers: DEFAULT_ICE_SERVERS }
          return this.iceConfiguration
        })
    }
    return this.iceConfigPromise
  }

  private markActive(): void {
    if (this.state.phase !== 'active') {
      stopRingtone()
      this.clearRingTimer()
      this.setState({ phase: 'active' })
    }
  }

  private async applyCandidate(
    pc: RTCPeerConnection,
    sessionId: string,
    candidate: RTCIceCandidateInit | null | undefined,
  ): Promise<void> {
    if (!candidate) return
    const key = candidateKey(candidate)
    if (!key) return
    const applied = this.appliedCandidates.get(sessionId) ?? new Set<string>()
    if (applied.has(key)) return
    await pc.addIceCandidate(new RTCIceCandidate(candidate))
    applied.add(key)
    this.appliedCandidates.set(sessionId, applied)
  }

  private async makePeerConnection(): Promise<RTCPeerConnection> {
    const configuration = await this.getIceConfiguration()
    const pc = new RTCPeerConnection(configuration)
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        const session = this.state.activeSession
        const other = session ? peerId(session, this.userId ?? '') : undefined
        if (session && other) {
          void signalCall(session.id, other, {
            type: 'candidate',
            candidate: event.candidate.toJSON(),
          }).catch(() => undefined)
        }
      }
    }
    pc.ontrack = (event) => {
      const stream = event.streams[0]
      if (stream && this.remoteAudio) {
        this.remoteAudio.srcObject = stream
        // `autoplay` usually starts playback; an explicit play() keeps the
        // remote audio audible when srcObject is assigned after the element
        // was already rendered (e.g. the callee accepts a little late).
        void this.remoteAudio.play().catch(() => undefined)
      }
      // Media is flowing — ensure UI reflects active call even if
      // connectionState event was missed, delayed, or already fired.
      this.markActive()
    }
    pc.onconnectionstatechange = () => {
      const connectionState = pc.connectionState
      if (connectionState === 'connected') {
        stopRingtone()
        this.clearRingTimer()
        this.markActive()
        if (this.activeSessionId) {
          void updateCallStatus(this.activeSessionId, 'IN_PROGRESS').catch(() => undefined)
        }
      } else if (connectionState === 'connecting' || connectionState === 'new') {
        stopRingtone()
        this.clearRingTimer()
        if (this.state.phase === 'active') {
          this.setState({ phase: 'connecting' })
        }
      } else if (connectionState === 'disconnected') {
        // ICE can recover from a transient disconnect; keep the call open but
        // surface that the link is re-establishing rather than claiming active.
        if (this.state.phase === 'active') {
          this.setState({ phase: 'connecting' })
        }
      } else if (connectionState === 'failed') {
        this.setState({
          error: 'The audio connection failed. Check your network and try again.',
        })
        this.endSession('The call could not be connected.')
      } else if (connectionState === 'closed') {
        this.endSession()
      }
    }
    this.pc = pc
    return pc
  }

  private async flushCandidates(pc: RTCPeerConnection, sessionId: string): Promise<void> {
    const buffered = this.pendingCandidates.get(sessionId)
    if (buffered) {
      this.pendingCandidates.delete(sessionId)
      for (const candidate of buffered) {
        try {
          await this.applyCandidate(pc, sessionId, candidate)
        } catch {
          // Late or redundant candidates are safe to ignore.
        }
      }
    }
    // Recover candidates persisted on the server when the realtime delivery
    // was missed so the two peers can still establish media connectivity.
    try {
      const session = await getCall(sessionId)
      for (const item of session.ice_candidates ?? []) {
        if (!item || item.from_user === this.userId) continue
        try {
          await this.applyCandidate(pc, sessionId, item.candidate)
        } catch {
          // Redundant or expired candidates are safe to ignore.
        }
      }
    } catch {
      // The realtime candidate stream may still deliver a moment later.
    }
  }

  private async recoverAnswer(sessionId: string): Promise<void> {
    const pc = this.pc
    if (!pc || pc.remoteDescription || this.state.role !== 'caller') return
    try {
      const session = await getCall(sessionId)
      if (session.answer_sdp && session.answer_from && session.answer_from !== this.userId) {
        await pc.setRemoteDescription({ type: 'answer', sdp: session.answer_sdp })
        await this.flushCandidates(pc, sessionId)
        // After recovering a missed answer, ensure the UI leaves ringing.
        if (pc.connectionState === 'connected') {
          stopRingtone()
          this.setState({ phase: 'active' })
        } else if (this.state.phase === 'ringing') {
          stopRingtone()
          this.setState({ phase: 'connecting' })
        }
      }
    } catch {
      // The realtime answer will arrive shortly; nothing to recover.
    }
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  private endSession(notice = ''): void {
    this.clearRingTimer()
    this.closePeer()
    this.activeSessionId = null
    stopRingtone()
    this.setState({
      phase: 'ended',
      role: null,
      activeSession: null,
      incomingSession: null,
      notice,
    })
    if (this.noticeTimer !== null) window.clearTimeout(this.noticeTimer)
    if (notice) {
      this.noticeTimer = window.setTimeout(() => {
        this.setState({ notice: '' })
        this.noticeTimer = null
      }, 4500)
    }
    window.setTimeout(() => {
      if (this.state.phase === 'ended') {
        this.setState({ phase: 'idle', error: '' })
      }
    }, 1500)
  }

  // ---------------------------------------------------------------------------
  // Outgoing calls
  // ---------------------------------------------------------------------------

  async startCall(recipientId: string): Promise<void> {
    if (!recipientId || this.starting || this.state.activeSession) return
    this.starting = true
    this.setState({ error: '', notice: '', starting: true })
    let created: CallSession
    try {
      created = await createCall(recipientId, null, 'WEBRTC')
    } catch (exception) {
      this.starting = false
      this.setState({
        error: exception instanceof AppApiError ? exception.message : 'Could not start the call.',
        starting: false,
      })
      return
    }
    this.starting = false
    this.activeSessionId = created.id
    this.setState({ activeSession: created, role: 'caller', phase: 'ringing', starting: false })
    startRingtone('ringback')
    try {
      const stream = await this.startMedia()
      const pc = await this.makePeerConnection()
      stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      const other = peerId(created, this.userId ?? '')
      if (other) {
        await signalCall(created.id, other, { type: 'offer', sdp: offer.sdp ?? '' })
      }
      await updateCallStatus(created.id, 'RINGING')
    } catch {
      this.setState({ error: 'Microphone access is required to place a call.' })
      await updateCallStatus(created.id, 'FAILED').catch(() => undefined)
      this.endSession()
    }
  }

  // ---------------------------------------------------------------------------
  // Incoming calls
  // ---------------------------------------------------------------------------

  /**
   * Waits for the WebRTC offer for a session, recovering it from the server if
   * the realtime delivery was missed. Returns the offer, 'expired' when the
   * call is already terminal, or null when the caller has not connected yet.
   */
  private async waitForOffer(
    sessionId: string,
    timeoutMs = 6000,
  ): Promise<{ fromUser: string; sdp: string } | 'expired' | null> {
    const deadline = Date.now() + timeoutMs
    while (Date.now() < deadline) {
      const cached = this.offers.get(sessionId)
      if (cached) return cached
      try {
        const session = await getCall(sessionId)
        if (TERMINAL_STATUSES.includes(session.status)) return 'expired'
        if (session.offer_sdp) {
          return { fromUser: session.offer_from ?? '', sdp: session.offer_sdp }
        }
        // Ask the caller to resend the offer in case their delivery failed.
        const other = peerId(session, this.userId ?? '')
        if (other) {
          void signalCall(sessionId, other, { type: 'request_offer' }).catch(() => undefined)
        }
      } catch {
        // Transient server error; retry until the deadline.
      }
      await sleep(700)
    }
    return this.offers.get(sessionId) ?? null
  }

  async accept(): Promise<void> {
    const incoming = this.state.incomingSession
    if (!incoming || this.accepting) return
    this.accepting = true
    this.clearRingTimer()
    this.setState({ error: '', notice: '', accepting: true })
    stopRingtone()
    const offer = await this.waitForOffer(incoming.id)
    if (offer === 'expired') {
      this.accepting = false
      this.setState({ accepting: false, incomingSession: null })
      return
    }
    if (!offer) {
      this.accepting = false
      this.setState({
        accepting: false,
        error: 'The caller has not connected yet. Please wait a moment and try again.',
      })
      return
    }
    this.activeSessionId = incoming.id
    this.accepting = false
    this.setState({
      incomingSession: null,
      activeSession: incoming,
      role: 'callee',
      phase: 'connecting',
      accepting: false,
    })
    try {
      const stream = await this.startMedia()
      const pc = await this.makePeerConnection()
      stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
      await pc.setRemoteDescription({ type: 'offer', sdp: offer.sdp })
      await this.flushCandidates(pc, incoming.id)
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      const other = peerId(incoming, this.userId ?? '')
      if (other) {
        await signalCall(incoming.id, other, { type: 'answer', sdp: answer.sdp ?? '' })
      }
      await updateCallStatus(incoming.id, 'IN_PROGRESS')
      // Stay on "Connecting…" until the peer connection is actually
      // established. The server status alone only confirms the callee tapped
      // Accept; it does not mean media is flowing. onconnectionstatechange /
      // ontrack promote the UI to active.
      stopRingtone()
      this.clearRingTimer()
      if (pc.connectionState === 'connected') {
        this.markActive()
      } else if (this.state.phase !== 'connecting') {
        this.setState({ phase: 'connecting' })
      }
    } catch {
      this.setState({ error: 'Could not answer the call. Please try again.' })
      await updateCallStatus(incoming.id, 'FAILED').catch(() => undefined)
      this.endSession()
    }
  }

  async decline(): Promise<void> {
    const incoming = this.state.incomingSession
    if (!incoming) return
    this.clearRingTimer()
    stopRingtone()
    this.setState({ incomingSession: null })
    const other = peerId(incoming, this.userId ?? '')
    if (other) {
      await signalCall(incoming.id, other, { type: 'bye' }).catch(() => undefined)
    }
    await updateCallStatus(incoming.id, 'DECLINED').catch(() => undefined)
  }

  async end(): Promise<void> {
    const session = this.state.activeSession
    if (!session) return
    stopRingtone()
    const other = peerId(session, this.userId ?? '')
    if (other) {
      await signalCall(session.id, other, { type: 'bye' }).catch(() => undefined)
    }
    await updateCallStatus(session.id, 'COMPLETED').catch(() => undefined)
    this.endSession()
  }

  toggleMute(): void {
    const next = !this.state.muted
    this.setState({ muted: next })
    if (this.localStream) {
      this.localStream.getAudioTracks().forEach((track) => {
        track.enabled = !next
      })
    }
  }

  // ---------------------------------------------------------------------------
  // Realtime + polling
  // ---------------------------------------------------------------------------

  handleRealtimeEvent(event: RealtimeEvent): void {
    if (event.type === 'call.initiated') {
      const sessionId = event.payload?.call_session_id
      if (!sessionId) return
      const initiatedBy = event.payload?.initiated_by
      if (initiatedBy && initiatedBy === this.userId) return
      void this.surfaceIncoming(sessionId)
      return
    }
    if (event.type === 'call.updated') {
      const sessionId = event.payload?.call_session_id
      const status = event.payload?.status
      if (!sessionId || !status) return
      this.handleStatusUpdate(sessionId, status)
      return
    }
    if (event.type !== 'call.signal') return
    const sessionId = event.payload?.call_session_id
    const data = event.payload?.data as SignalData | undefined
    if (!sessionId || !data) return

    if (data.type === 'offer') {
      this.offers.set(sessionId, { fromUser: event.payload?.from_user ?? '', sdp: data.sdp })
      return
    }
    if (data.type === 'answer') {
      const pc = this.pc
      if (sessionId === this.activeSessionId) {
        stopRingtone()
        this.clearRingTimer()
        if (this.state.phase === 'ringing') {
          this.setState({ phase: 'connecting' })
        }
        if (pc && !pc.remoteDescription) {
          void pc
            .setRemoteDescription({ type: 'answer', sdp: data.sdp })
            .then(() => this.flushCandidates(pc, sessionId))
            .then(() => {
              if (pc.connectionState === 'connected') {
                this.setState({ phase: 'active' })
              } else if (this.state.phase === 'ringing') {
                this.setState({ phase: 'connecting' })
              }
            })
            .catch(() => undefined)
        }
      }
      return
    }
    if (data.type === 'candidate') {
      const pc = this.pc
      if (pc && pc.remoteDescription) {
        void this.applyCandidate(pc, sessionId, data.candidate).catch(() => undefined)
      } else {
        const buffered = this.pendingCandidates.get(sessionId) ?? []
        buffered.push(data.candidate)
        this.pendingCandidates.set(sessionId, buffered)
      }
      return
    }
    if (data.type === 'bye') {
      if (
        this.state.activeSession?.id === sessionId ||
        this.state.incomingSession?.id === sessionId
      ) {
        this.endSession()
      }
      return
    }
    if (data.type === 'request_offer') {
      const pc = this.pc
      if (sessionId === this.activeSessionId && pc?.localDescription) {
        const session = this.state.activeSession ?? this.state.incomingSession
        const other = session ? peerId(session, this.userId ?? '') : undefined
        if (other) {
          void signalCall(sessionId, other, {
            type: 'offer',
            sdp: pc.localDescription.sdp,
          }).catch(() => undefined)
        }
      }
      return
    }
  }

  private handleStatusUpdate(sessionId: string, status: string): void {
    if (this.state.incomingSession?.id === sessionId) {
      if (TERMINAL_STATUSES.includes(status)) {
        this.clearRingTimer()
        stopRingtone()
        this.setState({ incomingSession: null })
        return
      }
      if (status === 'IN_PROGRESS') {
        // Callee answered (possibly on another tab) — ensure ring stops.
        // If we are the callee and already moved to activeSession via accept(),
        // the activeSession branch below will handle it; otherwise clear stale incoming.
        this.clearRingTimer()
        stopRingtone()
        if (!this.state.activeSession) {
          this.setState({ incomingSession: null })
        }
      }
      return
    }
    if (this.activeSessionId !== sessionId) return
    if (TERMINAL_STATUSES.includes(status)) {
      this.endSession(NOTICE_BY_STATUS[status] ?? '')
      return
    }
    if (status === 'IN_PROGRESS') {
      stopRingtone()
      this.clearRingTimer()
      // Server confirms the callee accepted. Leave the ringing UI, but do
      // not claim "active" before the peer connection is established — that
      // would show "Call in progress" while no audio is actually flowing.
      if (this.state.phase === 'ringing' || this.state.phase === 'connecting') {
        const connected = this.pc?.connectionState === 'connected' && this.pc?.remoteDescription
        this.setState({ phase: connected ? 'active' : 'connecting' })
      }
      if (this.state.role === 'caller') {
        // The callee answered; if the answer signal was lost, recover it from
        // the server so the call still connects.
        void this.recoverAnswer(sessionId)
      }
    }
  }

  /** Show the incoming-call UI for a session as soon as it is known. */
  private async surfaceIncoming(sessionId: string): Promise<void> {
    if (this.state.activeSession?.id === sessionId || this.state.incomingSession?.id === sessionId) {
      return
    }
    if (this.state.activeSession || this.state.incomingSession) return
    try {
      const session = await getCall(sessionId)
      if (this.userId && session.initiated_by === this.userId) return
      if (TERMINAL_STATUSES.includes(session.status)) return
      if (this.state.activeSession || this.state.incomingSession) return
      this.setState({ incomingSession: session, error: '', notice: '' })
      startRingtone('ring')
      this.scheduleRingTimeout(sessionId)
    } catch {
      // Transient; the background poll will pick the call up.
    }
  }

  /**
   * Background safety net: surfaces incoming calls and reflects server-side
   * states even when the realtime socket is down or events were missed while
   * the page was on another route.
   */
  private async pollForIncoming(): Promise<void> {
    if (!this.userId) return
    try {
      const calls = await getCalls()
      if (this.activeSessionId) {
        const current = calls.find((item) => item.id === this.activeSessionId)
        if (current && TERMINAL_STATUSES.includes(current.status)) {
          this.endSession(NOTICE_BY_STATUS[current.status] ?? '')
          return
        }
        // The peer answered on the server (IN_PROGRESS), but our realtime
        // `call.signal` (answer) and `call.updated` (IN_PROGRESS) events never
        // arrived — e.g. the socket reconnected or the channel-layer message
        // was dropped. Without this recovery the caller stays stuck on
        // "Ringing…" and the WebRTC answer is never applied, so the two ends
        // never actually connect even though the callee is already "active".
        // handleStatusUpdate both leaves ringing and recovers the answer.
        if (
          current &&
          current.status === 'IN_PROGRESS' &&
          (this.state.phase === 'ringing' || this.state.phase === 'connecting')
        ) {
          this.handleStatusUpdate(this.activeSessionId, 'IN_PROGRESS')
        }
        // The peer might still be trickling ICE candidates after our first
        // flush. Re-apply server-persisted candidates on each poll; they are
        // deduplicated so this is cheap and idempotent.
        if (this.activeSessionId && this.pc?.remoteDescription) {
          void this.flushCandidates(this.pc, this.activeSessionId).catch(() => undefined)
        }
      }
      if (this.state.activeSession || this.state.incomingSession) return
      const incoming = calls.find(
        (item) => item.initiated_by !== this.userId && !TERMINAL_STATUSES.includes(item.status),
      )
      if (incoming) {
        this.setState({ incomingSession: incoming, error: '', notice: '' })
        startRingtone('ring')
        this.scheduleRingTimeout(incoming.id)
      }
    } catch {
      // Transient; try again on the next tick.
    }
  }
}

export const callManager = new CallManager()

export function useCallManager(): CallState {
  return useSyncExternalStore(callManager.subscribe, callManager.getSnapshot)
}
