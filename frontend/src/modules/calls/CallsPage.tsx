import { useQuery } from '@tanstack/react-query'
import { Phone } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { callManager, useCallManager } from '../../shared/calls/callManager'
import { primeAudio } from '../../shared/calls/ringtone'
import { Button } from '../../shared/ui/actions/Button'
import { StatusBadge } from '../../shared/ui/data-display/StatusBadge'
import { Alert } from '../../shared/ui/feedback/Alert'
import { EmptyState } from '../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../shared/ui/feedback/SectionLoader'
import { SelectField } from '../../shared/ui/forms/SelectField'
import { PageHeader } from '../../shared/ui/navigation/PageHeader'
import { getCallAvailability, getCalls, getEligibleContacts } from '../communication/shared/api'

export function CallsPage() {
  const callState = useCallManager()

  const availability = useQuery({ queryKey: ['call-availability'], queryFn: getCallAvailability })
  const contacts = useQuery({ queryKey: ['eligible-contacts'], queryFn: getEligibleContacts })
  const calls = useQuery({ queryKey: ['calls'], queryFn: getCalls, refetchInterval: 20_000 })

  const [recipient, setRecipient] = useState('')

  const busy = Boolean(callState.activeSession)

  // Launch a call directly when arriving from a conversation (?recipient=...).
  const [searchParams, setSearchParams] = useSearchParams()
  const autoStartedRef = useRef(false)
  useEffect(() => {
    if (autoStartedRef.current) return
    const paramRecipient = searchParams.get('recipient')
    if (!paramRecipient) return
    if (!contacts.data) return
    if (!contacts.data.some((contact) => contact.id === paramRecipient)) return
    autoStartedRef.current = true
    setRecipient(paramRecipient)
    void callManager.startCall(paramRecipient)
    setSearchParams({}, { replace: true })
  }, [contacts.data, searchParams, setSearchParams])

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
              <Phone />
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
            disabled={!recipient || busy || callState.starting}
            isLoading={callState.starting}
            onClick={() => {
              primeAudio()
              void callManager.startCall(recipient)
            }}
          >
            <Phone size={16} /> Start call
          </Button>
        </section>
      )}
      {callState.error && <Alert tone="critical">{callState.error}</Alert>}
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
      <p className="section-hint">
        Calls ring on every page, not only here. Answer or decline from the on-screen call card
        wherever you are in Velora.
      </p>
    </div>
  )
}
