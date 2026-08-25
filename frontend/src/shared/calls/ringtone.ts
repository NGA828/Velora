/**
 * Best-effort WebAudio ringtone for incoming calls and ringback for outgoing
 * calls. Browsers may block audio until the user has interacted with the page;
 * every failure is swallowed so calling never depends on sound working.
 */

let context: AudioContext | null = null
let oscillator: OscillatorNode | null = null
let patternTimer: number | null = null

function ensureContext(): AudioContext | null {
  try {
    if (!context) {
      const Ctor =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Ctor) return null
      context = new Ctor()
    }
    if (context.state === 'suspended') {
      void context.resume().catch(() => undefined)
    }
    return context
  } catch {
    return null
  }
}

export function primeAudio(): void {
  ensureContext()
}

interface RingPattern {
  /** Duration of each audible burst, milliseconds. */
  burst: number
  /** Frequency while audible. */
  frequency: number
  /** Volume (0..1); keep low so it does not feed back into an open mic. */
  volume: number
}

const RING: RingPattern = { burst: 900, frequency: 440, volume: 0.1 }
const RINGBACK: RingPattern = { burst: 300, frequency: 425, volume: 0.06 }

export function startRingtone(variant: 'ring' | 'ringback' = 'ring'): void {
  stopRingtone()
  const ctx = ensureContext()
  if (!ctx) return
  try {
    const osc = ctx.createOscillator()
    const vol = ctx.createGain()
    const pattern = variant === 'ring' ? RING : RINGBACK
    osc.type = 'sine'
    osc.frequency.value = pattern.frequency
    vol.gain.value = 0
    osc.connect(vol)
    vol.connect(ctx.destination)
    osc.start()
    let audible = false
    const apply = () => {
      audible = !audible
      const now = ctx.currentTime
      vol.gain.cancelScheduledValues(now)
      vol.gain.setValueAtTime(audible ? pattern.volume : 0, now)
      vol.gain.linearRampToValueAtTime(audible ? pattern.volume : 0, now + 0.04)
    }
    apply()
    patternTimer = window.setInterval(apply, pattern.burst)
    oscillator = osc
  } catch {
    stopRingtone()
  }
}

export function stopRingtone(): void {
  if (patternTimer !== null) {
    window.clearInterval(patternTimer)
    patternTimer = null
  }
  if (oscillator) {
    try {
      oscillator.stop()
    } catch {
      // already stopped
    }
    oscillator = null
  }
}
