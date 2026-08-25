import { apiClient } from '../../shared/api/client'
import type { AssistantSession, ChatResponse, ClinicalContext } from './types'

export async function sendChatMessage(
  patientId: string,
  message: string,
  sessionId?: string,
): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/clinical-assistant/chat/', {
    patient_id: patientId,
    message,
    session_id: sessionId || null,
  })
  return response.data
}

export async function getAssistantSessions(patientId?: string): Promise<AssistantSession[]> {
  const params = patientId ? { patient: patientId } : {}
  const response = await apiClient.get<{ data: AssistantSession[] }>('/clinical-assistant/sessions/', {
    params,
  })
  return response.data.data
}

export async function getAssistantSession(sessionId: string): Promise<AssistantSession> {
  const response = await apiClient.get<AssistantSession>(`/clinical-assistant/sessions/${sessionId}/`)
  return response.data
}

export async function clearAssistantSession(sessionId: string): Promise<void> {
  await apiClient.post(`/clinical-assistant/sessions/${sessionId}/clear/`)
}

export async function getPatientClinicalContext(patientId: string): Promise<ClinicalContext> {
  const response = await apiClient.get<ClinicalContext>('/clinical-assistant/sessions/context/', {
    params: { patient: patientId },
  })
  return response.data
}
