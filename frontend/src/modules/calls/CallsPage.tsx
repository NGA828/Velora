import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Phone, PhoneCall, PhoneOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { Call as TwilioCall, Device as TwilioDevice } from '@twilio/voice-sdk'

import { AppApiError } from '../../shared/api/errors'
import { Button } from '../../shared/ui/actions/Button'
import { StatusBadge } from '../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../shared/ui/feedback/Alert'
import { EmptyState } from '../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../shared/ui/feedback/SectionLoader'
import { SelectField } from '../../shared/ui/forms/SelectField'
import { PageHeader } from '../../shared/ui/navigation/PageHeader'
import { createCall, getCallAvailability, getCalls, getEligibleContacts, getVoiceToken } from '../communication/shared/api'

export function CallsPage() {
  const client = useQueryClient()
  const deviceRef = useRef<TwilioDevice | null>(null)
  const [activeCall, setActiveCall] = useState<TwilioCall | null>(null)
  const [incomingCall, setIncomingCall] = useState<TwilioCall | null>(null)
  const [recipient, setRecipient] = useState('')
  const [deviceError, setDeviceError] = useState('')
  const availability = useQuery({ queryKey: ['call-availability'], queryFn: getCallAvailability })
  const contacts = useQuery({ queryKey: ['eligible-contacts'], queryFn: getEligibleContacts })
  const calls = useQuery({ queryKey: ['calls'], queryFn: getCalls, refetchInterval: 20_000 })

  useEffect(() => {
    if (!availability.data?.available) return
    let disposed = false
    void (async () => {
      try {
        const [{ Device }, token] = await Promise.all([import('@twilio/voice-sdk'), getVoiceToken()])
        if (disposed) return
        const device = new Device(token.token, { logLevel: 1 })
        device.on('incoming', (call) => setIncomingCall(call))
        device.on('error', (error) => setDeviceError(error.message))
        await device.register()
        deviceRef.current = device
      } catch (error) {
        setDeviceError(error instanceof Error ? error.message : 'Twilio device setup failed.')
      }
    })()
    return () => { disposed = true; deviceRef.current?.destroy(); deviceRef.current = null }
  }, [availability.data?.available])

  const callMutation = useMutation({
    mutationFn: async () => {
      if (!deviceRef.current) throw new Error('The Twilio voice device is not ready.')
      const session = await createCall(recipient)
      const call = await deviceRef.current.connect({ params: { call_session_id: session.id } })
      setActiveCall(call)
      call.on('disconnect', () => { setActiveCall(null); void client.invalidateQueries({ queryKey: ['calls'] }) })
      call.on('cancel', () => setActiveCall(null))
      return session
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ['calls'] }),
  })
  const acceptIncoming = () => { if (!incomingCall) return; incomingCall.accept(); setActiveCall(incomingCall); setIncomingCall(null); incomingCall.on('disconnect', () => setActiveCall(null)) }
  const rejectIncoming = () => { incomingCall?.reject(); setIncomingCall(null) }
  const hangUp = () => { activeCall?.disconnect(); deviceRef.current?.disconnectAll(); setActiveCall(null) }

  return <div className="workspace-page workspace-page--narrow"><PageHeader eyebrow="Voice communication" title="Calls" description="Twilio-backed call sessions with persisted provider status and participant history." />{availability.isPending ? <SectionLoader /> : !availability.data?.available ? <Alert tone="information" title="Voice calling is not configured">Twilio credentials, a TwiML application and signed webhook base URL are required. No simulated call is started.</Alert> : <section className="section-panel call-control"><div><span className="call-control__icon"><PhoneCall /></span><div><h2>Start secure voice call</h2><p>Select an authorized contact. Twilio handles media; Velora stores call state, not audio.</p></div></div><SelectField label="Contact" value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="">Select authorized contact</option>{contacts.data?.map((contact) => <option key={contact.id} value={contact.id}>{contact.full_name} · {contact.role_label}</option>)}</SelectField><Button disabled={!recipient || Boolean(activeCall)} isLoading={callMutation.isPending} onClick={() => callMutation.mutate()}><Phone size={16} /> Start call</Button></section>}{(deviceError || callMutation.error) && <Alert tone="critical">{deviceError || (callMutation.error instanceof AppApiError ? callMutation.error.message : callMutation.error instanceof Error ? callMutation.error.message : 'Call failed.')}</Alert>}{incomingCall && <section className="incoming-call"><div><span className="call-pulse"><Phone /></span><div><strong>Incoming authorized call</strong><small>Twilio Voice</small></div></div><Button onClick={acceptIncoming}><Phone size={16} /> Accept</Button><Button variant="danger" onClick={rejectIncoming}><PhoneOff size={16} /> Decline</Button></section>}{activeCall && <section className="active-call"><span className="call-pulse"><PhoneCall /></span><div><strong>Call in progress</strong><small>Connected through Twilio Voice</small></div><Button variant="danger" onClick={hangUp}><PhoneOff size={16} /> End call</Button></section>}<section className="section-panel table-panel"><div className="section-panel__heading"><div><p className="eyebrow">Call records</p><h2>History</h2></div></div>{calls.isPending ? <SectionLoader /> : (calls.data?.length ?? 0) === 0 ? <EmptyState title="No calls recorded" description="Real Twilio call sessions will appear here." /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Participants</th><th>Initiated</th><th>Answered</th><th>Ended</th><th>Status</th></tr></thead><tbody>{calls.data!.map((call) => <tr key={call.id}><td><strong>{call.participants.map((item) => item.full_name).join(' ↔ ')}</strong><small>{call.patient_name || 'No patient context'}</small></td><td>{new Date(call.initiated_at).toLocaleString()}</td><td>{call.answered_at ? new Date(call.answered_at).toLocaleTimeString() : '—'}</td><td>{call.ended_at ? new Date(call.ended_at).toLocaleTimeString() : '—'}</td><td><StatusBadge status={call.status} /></td></tr>)}</tbody></table></div>}</section></div>
}
