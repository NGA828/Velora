import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createCall,
  getCall,
  getCalls,
  signalCall,
  updateCallStatus,
} from '../../modules/communication/shared/api'
import type { CallSession } from '../../modules/communication/shared/types'
import { callManager } from './callManager'

vi.mock('../../modules/communication/shared/api', () => ({
  createCall: vi.fn(),
  getCall: vi.fn(),
  getCalls: vi.fn(),
  signalCall: vi.fn(),
  updateCallStatus: vi.fn(),
}))

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
  }
  async setRemoteDescription(description: RTCSessionDescriptionInit): Promise<void> {
    this.remoteDescription = description as RTCSessionDescription
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
  pcInstances = []
  vi.stubGlobal('RTCPeerConnection', FakeRTCPeerConnection)
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
    expect(getCall).toHaveBeenCalledWith('s6')
  })
})
