import { Mic, MicOff, Phone, PhoneCall, PhoneOff } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { subscribeRealtime } from '../realtime/bus'
import { Button } from '../ui/actions/Button'
import { callManager, peerName, useCallManager, type CallPhase } from './callManager'
import { primeAudio } from './ringtone'

const PHASE_LABEL: Record<CallPhase, string> = {
  idle: '',
  ringing: 'Ringing…',
  incoming: 'Incoming call',
  connecting: 'Connecting…',
  active: 'Call in progress',
  ended: 'Call ended',
}

/**
 * Global in-app call UI. Mounted in the application shell so incoming calls
 * ring and can be answered or declined from any page, like WhatsApp.
 */
export function CallOverlay({ userId }: { userId: string }) {
  const state = useCallManager()
  const localAudioRef = useRef<HTMLAudioElement | null>(null)
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    callManager.configure(userId)
    callManager.startPolling()
    const unsubscribe = subscribeRealtime((event) => callManager.handleRealtimeEvent(event))
    // Unlock WebAudio on the next user gesture so the ringtone can play.
    const unlock = () => primeAudio()
    window.addEventListener('pointerdown', unlock)
    window.addEventListener('keydown', unlock)
    return () => {
      unsubscribe()
      callManager.stopPolling()
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      // The shell is unmounting (e.g. sign-out): stop any active microphone
      // capture and tear the call state down.
      callManager.dispose()
    }
  }, [userId])

  // Bind the audio elements while a call UI is mounted.
  useEffect(() => {
    callManager.setAudioElements(localAudioRef.current, remoteAudioRef.current)
  }, [state.activeSession?.id, state.phase])

  const incoming = state.incomingSession
  const active = state.activeSession

  return (
    <>
      {incoming && (
        <div className="call-overlay" role="dialog" aria-modal="false" aria-label="Incoming call">
          <div className="call-overlay__card">
            <span className="call-pulse">
              <Phone />
            </span>
            <p className="eyebrow">Incoming call</p>
            <h2>{peerName(incoming, userId)}</h2>
            <p className="call-overlay__hint">Secure in-app voice call</p>
            {state.error && <p className="call-overlay__error">{state.error}</p>}
            <div className="call-overlay__actions">
              <Button
                variant="danger"
                disabled={state.accepting}
                onClick={() => void callManager.decline()}
              >
                <PhoneOff size={16} /> Decline
              </Button>
              <Button
                disabled={state.accepting}
                isLoading={state.accepting}
                onClick={() => {
                  primeAudio()
                  void callManager.accept()
                }}
              >
                <Phone size={16} /> Accept
              </Button>
            </div>
          </div>
        </div>
      )}
      {active && (
        <div className="call-bar" role="status" aria-label="Active call">
          <span className="call-pulse">
            <PhoneCall />
          </span>
          <div className="call-bar__copy">
            <strong>{PHASE_LABEL[state.phase] || 'Call'}</strong>
            <small>
              {peerName(active, userId)} · {state.role === 'caller' ? 'Outgoing' : 'Incoming'}
            </small>
            {state.error && <small className="call-bar__error">{state.error}</small>}
          </div>
          {/* Local (muted) keeps the captured track alive; remote is audible. */}
          <audio ref={localAudioRef} muted autoPlay playsInline />
          <audio ref={remoteAudioRef} autoPlay playsInline />
          {state.phase === 'active' && (
            <Button
              variant="secondary"
              onClick={() => callManager.toggleMute()}
              aria-label={state.muted ? 'Unmute' : 'Mute'}
            >
              {state.muted ? <MicOff size={16} /> : <Mic size={16} />}
              {state.muted ? 'Unmute' : 'Mute'}
            </Button>
          )}
          {state.phase !== 'ended' && (
            <Button variant="danger" onClick={() => void callManager.end()}>
              <PhoneOff size={16} /> End call
            </Button>
          )}
        </div>
      )}
      {state.notice && (
        <div className="call-toast" role="status">
          {state.notice}
        </div>
      )}
    </>
  )
}
