import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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
import { callManager } from './callManager'

vi.mock('../../modules/communication/shared/api', () => ({
  createCall: vi.fn(),
  getCall: vi.fn(),
  getCalls: vi.fn(),
  getIceConfig: vi.fn(),
  signalCall: vi.fn(),
  updateCallStatus: vi.fn(),
}))

class FakeRTCIceCandidate {
  candidate: RTCIceCandidateInit
  constructor(init: RTCIceCandidateInit) {
    this.candidate = init
  }
}

class FakePeerConnection {
  localDescription: RTCSessionDescription | null = null
  remoteDescription: RTCSessionDescription | null = null
  connectionState = 'new'
  onicecandidate: ((event: { candidate: RTCIceCandidate | null }) => void) | null = null
  ontrack: ((event: { streams: MediaStream[] }) => void) | null = null
  onconnectionstatechange: (() => void) | null = null
  addTrack = vi.fn()
  addIceCandidate = vi.fn().mockResolvedValue(undefined)
  close = vi.fn()
  async createOffer(): Promise<RTCSessionDescriptionInit> {
    return { type: 'offer', sdp: 'fake-offer-sdp' }
  }
  async createAnswer(): Promise<RTCSessionDescriptionInit> {
    return { type: 'answer', sdp: 'fake-answer-sdp' }
  }
  async setLocalDescription(description: RTCSessionDescriptionInit): Promise<void> {
    this.localDescription = description as RTCSessionDescription
    if (description.type === 'answer') this.connectionState = 'connected'
  }
  async setRemoteDescription(description: RTCSessionDescriptionInit): Promise<void> {
    this.remoteDescription = description as RTCSessionDescription
    if (description.type === 'answer') this.connectionState = 'connected'
  }
}

let pcInstances: FakePeerConnection[] = []

class FakeRTCPeerConnection extends FakePeerConnection {
  constructor() {
    super()
    pcInstances.push(this)
  }
}

const lastPC = () => pcInstances[pcInstances.length - 1]

function fakeStream(): MediaStream {
  const track = { stop: vi.fn(), enabled: true }
  return {
    getAudioTracks: () => [track],
    getTracks: () => [track],
  } as unknown as MediaStream
}

function makeSession(overrides: Partial<CallSession>): CallSession {
  return {
    id: 's1',
    conversation: null,
    patient: null,
    patient_name: null,
    initiated_by: 'them',
    initiated_by_name: 'Dr. Them',
    provider: 'WEBRTC',
    provider_sid: '',
    direction: 'OUTBOUND',
    status: 'QUEUED',
    initiated_at: '2026-08-25T10:00:00Z',
    ringing_at: null,
    answered_at: null,
    ended_at: null,
    failure_reason: '',
    offer_sdp: null,
    offer_from: null,
    answer_sdp: null,
    answer_from: null,
    participants: [
      {
        id: 'p1',
        user_id: 'them',
        full_name: 'Dr. Them',
        role: 'DOCTOR',
        provider_identity: '',
        status: 'INVITED',
        joined_at: null,
        left_at: null,
      },
      {
        id: 'p2',
        user_id: 'me',
        full_name: 'Me User',
        role: 'NURSE',
        provider_identity: '',
        status: 'INVITED',
        joined_at: null,
        left_at: null,
      },
    ],
    ...overrides,
  }
}

beforeEach(() => {
  // resetAllMocks also drops mockResolvedValue implementations so no state
  // leaks between tests.
  vi.resetAllMocks()
  vi.mocked(signalCall).mockResolvedValue(undefined)
  vi.mocked(updateCallStatus).mockResolvedValue(makeSession({ id: 'x' }))
  vi.mocked(getCalls).mockResolvedValue([])
  vi.mocked(getIceConfig).mockResolvedValue({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
  })
  pcInstances = []
  vi.stubGlobal('RTCPeerConnection', FakeRTCPeerConnection)
  vi.stubGlobal('RTCIceCandidate', FakeRTCIceCandidate)
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn().mockResolvedValue(fakeStream()) },
    configurable: true,
  })
  callManager.dispose()
  callManager.configure('me')
})

afterEach(() => {
  callManager.dispose()
  vi.unstubAllGlobals()
})

describe('callManager incoming calls (any page)', () => {
  it('surfaces an incoming call from the call.initiated realtime event without visiting /calls', async () => {
    const session = makeSession({ id: 's1', status: 'RINGING' })
    vi.mocked(getCall).mockResolvedValue(session)

    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's1', initiated_by: 'them' },
    })

    await vi.waitFor(() => {
      expect(callManager.getSnapshot().incomingSession?.id).toBe('s1')
    })
    expect(getCall).toHaveBeenCalledWith('s1')
    expect(callManager.getSnapshot().incomingSession?.initiated_by).toBe('them')
  })

  it('ignores its own initiation events', async () => {
    vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's1', initiated_by: 'me' }))

    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's1', initiated_by: 'me' },
    })

    // No fetch is issued for calls the current user initiated themselves.
    await new Promise((resolve) => window.setTimeout(resolve, 20))
    expect(getCall).not.toHaveBeenCalled()
    expect(callManager.getSnapshot().incomingSession).toBeNull()
  })

  it('recovers a missed incoming call from the background poll', async () => {
    vi.mocked(getCalls).mockResolvedValue([makeSession({ id: 's3', status: 'RINGING' })])

    callManager.startPolling()
    try {
      await vi.waitFor(() => {
        expect(callManager.getSnapshot().incomingSession?.id).toBe('s3')
      })
    } finally {
      callManager.stopPolling()
    }
  })

  it('clears the incoming card when the caller cancels', async () => {
    vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's1', status: 'RINGING' }))
    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's1', initiated_by: 'them' },
    })
    await vi.waitFor(() => {
      expect(callManager.getSnapshot().incomingSession?.id).toBe('s1')
    })

    callManager.handleRealtimeEvent({
      type: 'call.updated',
      payload: { call_session_id: 's1', status: 'CANCELLED' },
    })

    expect(callManager.getSnapshot().incomingSession).toBeNull()
  })

  it('marks an unanswered ring NO_ANSWER after the ring timeout (missed call)', async () => {
    vi.useFakeTimers()
    try {
      vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's1', status: 'RINGING' }))
      callManager.handleRealtimeEvent({
        type: 'call.initiated',
        payload: { call_session_id: 's1', initiated_by: 'them' },
      })
      await vi.waitFor(() => {
        expect(callManager.getSnapshot().incomingSession?.id).toBe('s1')
      })

      // The callee never answers; after the ring deadline the call is
      // recorded as NO_ANSWER (the server turns this into a missed-call
      // notification) and the ring stops.
      await vi.advanceTimersByTimeAsync(31_000)

      expect(updateCallStatus).toHaveBeenCalledWith('s1', 'NO_ANSWER')
      expect(callManager.getSnapshot().incomingSession).toBeNull()
      expect(callManager.getSnapshot().notice).toBe('Missed call')
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('callManager accept', () => {
  it('recovers the offer from the server when the realtime signal was missed', async () => {
    const session = makeSession({ id: 's2', offer_sdp: 'server-offer-sdp', offer_from: 'them' })
    vi.mocked(getCall).mockResolvedValue(session)
    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's2', initiated_by: 'them' },
    })
    await vi.waitFor(() => {
      expect(callManager.getSnapshot().incomingSession?.id).toBe('s2')
    })

    await callManager.accept()

    const state = callManager.getSnapshot()
    expect(state.activeSession?.id).toBe('s2')
    expect(state.role).toBe('callee')
    expect(state.incomingSession).toBeNull()
    expect(state.error).toBe('')
    // The persisted offer was applied to the peer connection instead of
    // showing the old "Recovering connection..." dead-end.
    expect(lastPC()?.remoteDescription?.sdp).toBe('server-offer-sdp')
    expect(signalCall).toHaveBeenCalledWith('s2', 'them', { type: 'answer', sdp: 'fake-answer-sdp' })
    expect(updateCallStatus).toHaveBeenCalledWith('s2', 'IN_PROGRESS')
  })

  it('uses the offer received over the realtime bus when available', async () => {
    vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's2', status: 'RINGING' }))
    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's2', initiated_by: 'them' },
    })
    await vi.waitFor(() => {
      expect(callManager.getSnapshot().incomingSession?.id).toBe('s2')
    })
    callManager.handleRealtimeEvent({
      type: 'call.signal',
      payload: {
        call_session_id: 's2',
        from_user: 'them',
        data: { type: 'offer', sdp: 'ws-offer-sdp' },
      },
    })

    await callManager.accept()

    expect(lastPC()?.remoteDescription?.sdp).toBe('ws-offer-sdp')
  })

  it('does not show or answer calls that were already cancelled', async () => {
    vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's2', status: 'CANCELLED' }))
    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's2', initiated_by: 'them' },
    })
    await new Promise((resolve) => window.setTimeout(resolve, 20))

    // Terminal sessions never surface an incoming card in the first place.
    expect(callManager.getSnapshot().incomingSession).toBeNull()
    await callManager.accept()
    expect(callManager.getSnapshot().activeSession).toBeNull()
    expect(signalCall).not.toHaveBeenCalled()
  })

  it('declines by notifying the caller and recording DECLINED', async () => {
    vi.mocked(getCall).mockResolvedValue(makeSession({ id: 's4', status: 'RINGING' }))
    callManager.handleRealtimeEvent({
      type: 'call.initiated',
      payload: { call_session_id: 's4', initiated_by: 'them' },
    })
    await vi.waitFor(() => {
      expect(callManager.getSnapshot().incomingSession?.id).toBe('s4')
    })

    await callManager.decline()

    expect(callManager.getSnapshot().incomingSession).toBeNull()
    expect(signalCall).toHaveBeenCalledWith('s4', 'them', { type: 'bye' })
    expect(updateCallStatus).toHaveBeenCalledWith('s4', 'DECLINED')
  })
})

describe('callManager outgoing calls', () => {
  it('starts a call, creates an offer and marks the session RINGING', async () => {
    const session = makeSession({ id: 's5', initiated_by: 'me', status: 'QUEUED' })
    vi.mocked(createCall).mockResolvedValue(session)

    await callManager.startCall('them')

    const state = callManager.getSnapshot()
    expect(state.role).toBe('caller')
    expect(state.phase).toBe('ringing')
    expect(state.activeSession?.id).toBe('s5')
    expect(signalCall).toHaveBeenCalledWith('s5', 'them', { type: 'offer', sdp: 'fake-offer-sdp' })
    expect(updateCallStatus).toHaveBeenCalledWith('s5', 'RINGING')
    expect(createCall).toHaveBeenCalledWith('them', null, 'WEBRTC')
  })

  it('recovers the answer from the server when the realtime answer was missed', async () => {
    const session = makeSession({
      id: 's6',
      initiated_by: 'me',
      answer_sdp: 'server-answer-sdp',
      answer_from: 'them',
    })
    vi.mocked(createCall).mockResolvedValue(session)
    vi.mocked(getCall).mockResolvedValue(session)
    await callManager.startCall('them')

    // The callee answers; the answer signal is "lost", but the status update
    // arrives and triggers a server-side recovery.
    callManager.handleRealtimeEvent({
      type: 'call.updated',
      payload: { call_session_id: 's6', status: 'IN_PROGRESS' },
    })

    await vi.waitFor(() => {
      expect(lastPC()?.remoteDescription?.sdp).toBe('server-answer-sdp')
    })
    // The caller leaves "Ringing…" and reflects the connected call.
    expect(callManager.getSnapshot().phase).toBe('active')
    expect(getCall).toHaveBeenCalledWith('s6')
  })

  it('leaves "ringing" and recovers the answer when BOTH realtime events were missed but the poll sees IN_PROGRESS', async () => {
    // The callee answered on the server (status IN_PROGRESS + persisted
    // answer), but the caller's realtime `call.signal` (answer) AND
    // `call.updated` (IN_PROGRESS) events never arrived — e.g. the socket
    // reconnected or the page was on another route. The background poll is
    // the safety net: it must move the caller out of "ringing" and apply the
    // server answer so the two can actually communicate.
    const created = makeSession({ id: 's7', initiated_by: 'me', status: 'QUEUED' })
    vi.mocked(createCall).mockResolvedValue(created)
    const answered = makeSession({
      id: 's7',
      initiated_by: 'me',
      status: 'IN_PROGRESS',
      answer_sdp: 'server-answer-sdp',
      answer_from: 'them',
    })
    vi.mocked(getCalls).mockResolvedValue([answered])
    vi.mocked(getCall).mockResolvedValue(answered)

    await callManager.startCall('them')
    expect(callManager.getSnapshot().phase).toBe('ringing')

    callManager.startPolling()
    try {
      await vi.waitFor(() => {
        expect(callManager.getSnapshot().phase).toBe('active')
      })
    } finally {
      callManager.stopPolling()
    }
    // The caller applied the server-persisted answer so media can connect.
    expect(getCall).toHaveBeenCalledWith('s7')
    expect(lastPC()?.remoteDescription?.sdp).toBe('server-answer-sdp')
  })

  it('connects and leaves "ringing" when the callee answer signal arrives over realtime', async () => {
    const created = makeSession({ id: 's8', initiated_by: 'me', status: 'QUEUED' })
    vi.mocked(createCall).mockResolvedValue(created)
    await callManager.startCall('them')
    expect(callManager.getSnapshot().phase).toBe('ringing')

    callManager.handleRealtimeEvent({
      type: 'call.signal',
      payload: {
        call_session_id: 's8',
        from_user: 'them',
        data: { type: 'answer', sdp: 'callee-answer-sdp' },
      },
    })

    await vi.waitFor(() => {
      expect(callManager.getSnapshot().phase).not.toBe('ringing')
    })
    expect(lastPC()?.remoteDescription?.sdp).toBe('callee-answer-sdp')
  })

  it('applies server-persisted ICE candidates when the realtime candidate frames are lost', async () => {
    const created = makeSession({ id: 's9', initiated_by: 'me', status: 'QUEUED' })
    vi.mocked(createCall).mockResolvedValue(created)
    const answered = makeSession({
      id: 's9',
      initiated_by: 'me',
      status: 'IN_PROGRESS',
      answer_sdp: 'server-answer-sdp',
      answer_from: 'them',
      ice_candidates: [
        {
          from_user: 'them',
          candidate: {
            candidate: 'candidate:1 1 udp 2122260223 192.0.2.1 54321 typ host generation 0',
            sdpMid: '0',
            sdpMLineIndex: 0,
          },
        },
      ],
    })
    vi.mocked(getCall).mockResolvedValue(answered)

    await callManager.startCall('them')
    callManager.handleRealtimeEvent({
      type: 'call.updated',
      payload: { call_session_id: 's9', status: 'IN_PROGRESS' },
    })

    await vi.waitFor(() => {
      expect(lastPC()?.remoteDescription?.sdp).toBe('server-answer-sdp')
    })
    await vi.waitFor(() => {
      expect(lastPC()?.addIceCandidate).toHaveBeenCalled()
    })
  })

  it('shows a clear busy message when the recipient is already in a call', async () => {
    // Two people called each other at the same moment: the backend rejected
    // this initiation with 409 call_busy because the earlier session won.
    vi.mocked(createCall).mockRejectedValue(
      new AppApiError({
        message: 'This contact is calling you. Answer the incoming call instead of placing a new one.',
        status: 409,
        code: 'call_busy',
      }),
    )

    await callManager.startCall('them')

    const state = callManager.getSnapshot()
    expect(state.error).toContain('Answer the incoming call')
    expect(state.activeSession).toBeNull()
    expect(state.phase).toBe('idle')
    expect(state.starting).toBe(false)
  })
})
