import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, MessageCircle, Paperclip, PhoneCall, Plus, Send, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useSession } from '../auth/hooks/use-session'
import { getPatients } from '../patient-care/shared/api'
import { AppApiError } from '../../shared/api/errors'
import { Button } from '../../shared/ui/actions/Button'
import { Alert } from '../../shared/ui/feedback/Alert'
import { EmptyState } from '../../shared/ui/feedback/EmptyState'
import { SectionLoader } from '../../shared/ui/feedback/SectionLoader'
import { SelectField } from '../../shared/ui/forms/SelectField'
import { PageHeader } from '../../shared/ui/navigation/PageHeader'
import { Modal } from '../../shared/ui/overlays/Modal'
import { acknowledgeMessages, createConversation, getConversations, getEligibleContacts, getMessages, sendMessage } from '../communication/shared/api'

export function MessagesPage() {
  const { data: session } = useSession()
  const user = session!.user
  const client = useQueryClient()
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState('')
  const [newOpen, setNewOpen] = useState(false)
  const [contactId, setContactId] = useState('')
  const [patientId, setPatientId] = useState('')
  const [body, setBody] = useState('')
  const [attachment, setAttachment] = useState<File | undefined>()
  const fileRef = useRef<HTMLInputElement>(null)
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: getConversations, refetchInterval: 30_000 })
  const contacts = useQuery({ queryKey: ['eligible-contacts'], queryFn: getEligibleContacts })
  const careRole = ['DOCTOR', 'NURSE', 'PATIENT_GUARD'].includes(user.role)
  const patients = useQuery({ queryKey: ['patients', 'messages'], queryFn: () => getPatients(), enabled: careRole })
  const messages = useQuery({ queryKey: ['messages', selectedId], queryFn: () => getMessages(selectedId), enabled: Boolean(selectedId), refetchInterval: 15_000 })
  useEffect(() => { if (!selectedId && conversations.data?.[0]) setSelectedId(conversations.data[0].id) }, [conversations.data, selectedId])
  useEffect(() => { conversations.data?.forEach((conversation) => { const last = conversation.last_message; if (last && last.sender !== user.id && last.own_receipt && !last.own_receipt.delivered_at) void acknowledgeMessages(conversation.id, last.id, false) }) }, [conversations.data, user.id])
  useEffect(() => { const latest = messages.data?.[0]; if (selectedId && latest && latest.sender !== user.id && latest.own_receipt && !latest.own_receipt.seen_at) { void acknowledgeMessages(selectedId, latest.id, true).then(() => { void client.invalidateQueries({ queryKey: ['messages', selectedId] }); void client.invalidateQueries({ queryKey: ['conversations'] }) }) } }, [client, messages.data, selectedId, user.id])
  const selected = conversations.data?.find((item) => item.id === selectedId)
  const other = selected?.participants.find((item) => item.user_id !== user.id)
  const orderedMessages = useMemo(() => [...(messages.data ?? [])].reverse(), [messages.data])
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ['conversations'] }), client.invalidateQueries({ queryKey: ['messages', selectedId] })])
  const createMutation = useMutation({ mutationFn: () => createConversation({ participant: contactId, patient: patientId || null, subject: '' }), onSuccess: async (conversation) => { setNewOpen(false); setSelectedId(conversation.id); await refresh() } })
  const sendMutation = useMutation({ mutationFn: () => sendMessage(selectedId, body, attachment), onSuccess: async () => { setBody(''); setAttachment(undefined); if (fileRef.current) fileRef.current.value = ''; await refresh() } })
  return <div className="workspace-page communication-page"><PageHeader eyebrow="Secure communication" title="Messages" description="Durable conversations with real Sent, Delivered and Seen receipt states." actions={<Button onClick={() => { setNewOpen(true); setContactId(''); setPatientId('') }}><Plus size={16} /> New conversation</Button>} />{conversations.isPending ? <SectionLoader /> : <div className="messaging-layout"><aside className="conversation-list">{(conversations.data?.length ?? 0) === 0 ? <EmptyState title="No conversations" description="Start a conversation with an authorized hospital contact." /> : conversations.data!.map((conversation) => { const participant = conversation.participants.find((item) => item.user_id !== user.id); return <button key={conversation.id} className={conversation.id === selectedId ? 'conversation-row conversation-row--active' : 'conversation-row'} onClick={() => setSelectedId(conversation.id)}><span className="avatar">{participant?.full_name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span><span><strong>{participant?.full_name ?? 'Conversation'}</strong><small>{conversation.last_message?.body || conversation.last_message?.attachment?.original_name || 'No messages yet'}</small></span>{conversation.unread_count > 0 && <b>{conversation.unread_count}</b>}</button> })}</aside><section className="chat-panel">{!selected ? <EmptyState title="Select a conversation" description="Messages are loaded from the secure hospital API." /> : <><header><div><span className="avatar">{other?.full_name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span><div><strong>{other?.full_name}</strong><small>{other?.role_label}{selected.patient_name ? ` · ${selected.patient_name}` : ''}</small></div></div>{other && <button type="button" className="icon-button" aria-label={`Start a voice call with ${other.full_name}`} onClick={() => navigate(`/calls?recipient=${other.user_id}`)}><PhoneCall size={18} /></button>}</header><div className="message-stream">{messages.isPending ? <SectionLoader /> : orderedMessages.length === 0 ? <EmptyState title="No messages yet" description="Send the first message in this authorized conversation." /> : orderedMessages.map((message) => <article key={message.id} className={message.sender === user.id ? 'message-bubble message-bubble--own' : 'message-bubble'}><div>{message.body && <p>{message.body}</p>}{message.attachment && <a className="attachment-link" href={message.attachment.download_url}><FileText size={16} /><span><strong>{message.attachment.original_name}</strong><small>{Math.ceil(message.attachment.byte_size / 1024)} KB</small></span></a>}</div><footer>{new Date(message.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}{message.sender === user.id && <span>{message.delivery_state.toLowerCase()}</span>}</footer></article>)}</div><form className="message-composer" onSubmit={(event) => { event.preventDefault(); if (body.trim() || attachment) sendMutation.mutate() }}>{attachment && <div className="selected-attachment"><Paperclip size={15} /> {attachment.name}<button type="button" onClick={() => setAttachment(undefined)}><X size={14} /></button></div>}<div><input value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write a secure message…" aria-label="Message" /><input ref={fileRef} hidden type="file" accept=".pdf,.jpg,.jpeg,.png,.txt" onChange={(event) => setAttachment(event.target.files?.[0])} /><button type="button" className="icon-button" onClick={() => fileRef.current?.click()} aria-label="Attach file"><Paperclip /></button><Button type="submit" disabled={!body.trim() && !attachment} isLoading={sendMutation.isPending}><Send size={16} /> Send</Button></div>{sendMutation.error && <Alert tone="critical">{sendMutation.error instanceof AppApiError ? sendMutation.error.message : 'Message could not be sent.'}</Alert>}</form></>}</section></div>}
    <Modal open={newOpen} onClose={() => setNewOpen(false)} title="New conversation" description="Only contacts allowed by current staff and patient relationships are listed."><form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }}><SelectField label="Contact" required value={contactId} onChange={(event) => setContactId(event.target.value)}><option value="">Select authorized contact</option>{contacts.data?.map((contact) => <option key={contact.id} value={contact.id}>{contact.full_name} · {contact.role_label}</option>)}</SelectField>{careRole && <SelectField label="Patient context (optional)" value={patientId} onChange={(event) => setPatientId(event.target.value)}><option value="">No patient context</option>{patients.data?.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name} · {patient.medical_record_number}</option>)}</SelectField>}{createMutation.error && <Alert tone="critical">{createMutation.error instanceof AppApiError ? createMutation.error.message : 'Conversation could not be created.'}</Alert>}<div className="modal__actions"><Button type="button" variant="secondary" onClick={() => setNewOpen(false)}>Cancel</Button><Button type="submit" disabled={!contactId} isLoading={createMutation.isPending}><MessageCircle size={16} /> Start conversation</Button></div></form></Modal>
  </div>
}
