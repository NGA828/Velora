import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { CallSession, Conversation, EligibleContact, Message } from './types'

export async function getConversations(): Promise<Conversation[]> { return (await apiClient.get<PaginatedResponse<Conversation>>('/conversations/', { params: { page_size: 100 } })).data.data }
export async function getEligibleContacts(): Promise<EligibleContact[]> { return (await apiClient.get<EligibleContact[]>('/conversations/eligible/')).data }
export async function createConversation(payload: unknown): Promise<Conversation> { await prepareCsrf(); return (await apiClient.post<Conversation>('/conversations/', payload)).data }
export async function getMessages(conversation: string): Promise<Message[]> { return (await apiClient.get<PaginatedResponse<Message>>(`/conversations/${conversation}/messages/`, { params: { page_size: 100 } })).data.data }
export async function sendMessage(conversation: string, body: string, attachment?: File): Promise<Message> { await prepareCsrf(); const data = new FormData(); data.set('body', body); data.set('client_message_id', crypto.randomUUID()); if (attachment) data.set('attachment', attachment); return (await apiClient.post<Message>(`/conversations/${conversation}/messages/`, data)).data }
export async function acknowledgeMessages(conversation: string, upToMessage: string, seen: boolean): Promise<void> { await prepareCsrf(); await apiClient.post(`/conversations/${conversation}/${seen ? 'seen' : 'delivered'}/`, { up_to_message: upToMessage }) }
export async function getCallAvailability(): Promise<{ available: boolean }> { return (await apiClient.get<{ available: boolean }>('/calls/availability/')).data }
export async function getVoiceToken(): Promise<{ token: string; identity: string; expires_in: number }> { return (await apiClient.get('/calls/token/')).data }
export async function getCalls(): Promise<CallSession[]> { return (await apiClient.get<PaginatedResponse<CallSession>>('/calls/', { params: { page_size: 100 } })).data.data }
export async function getCall(id: string): Promise<CallSession> { return (await apiClient.get<CallSession>(`/calls/${id}/`)).data }
export async function createCall(recipient: string, conversation?: string | null, provider: 'WEBRTC' | 'TWILIO' = 'WEBRTC'): Promise<CallSession> { await prepareCsrf(); return (await apiClient.post<CallSession>('/calls/', { recipient, conversation: conversation || null, provider })).data }
export async function cancelCall(id: string): Promise<CallSession> { await prepareCsrf(); return (await apiClient.post<CallSession>(`/calls/${id}/cancel/`)).data }
export async function signalCall(id: string, toUser: string, data: unknown): Promise<void> { await prepareCsrf(); await apiClient.post(`/calls/${id}/signal/`, { to_user: toUser, data }) }
export async function updateCallStatus(id: string, callStatus: string): Promise<CallSession> { await prepareCsrf(); return (await apiClient.post<CallSession>(`/calls/${id}/status/`, { status: callStatus })).data }
