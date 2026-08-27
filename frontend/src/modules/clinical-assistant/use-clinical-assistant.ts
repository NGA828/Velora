import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { useSession } from '../auth/hooks/use-session'
import {
  clearAssistantSession,
  getAssistantSessions,
  getPatientClinicalContext,
  sendChatMessage,
} from './api'
import type { AssistantMessage, AssistantSession } from './types'

export const DOCTOR_SUGGESTED_PROMPTS = [
  'Why was this patient flagged for ICU assessment?',
  'Summarize the patient’s recent vital trends and stability.',
  'What clinical rules and thresholds were triggered?',
  'Explain current specialist availability and bed capacity.',
]

export const NURSE_SUGGESTED_PROMPTS = [
  'Summarize recent vital signs and critical alert status.',
  'What is the current ICU recommendation and rationale?',
  'What active medications and treatments are scheduled?',
]

export const GUARDIAN_SUGGESTED_PROMPTS = [
  'How is the patient currently doing?',
  'Why is the patient being monitored closely?',
  'Can you explain the latest care update in simple terms?',
  'What should I ask the medical team when I visit?',
]

export function useClinicalAssistant(patientId: string) {
  const queryClient = useQueryClient()
  const session = useSession()
  const userRole = session.data?.user.role

  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined)
  const [pendingMessages, setPendingMessages] = useState<string[]>([])

  // 1. Fetch Clinical Context for this patient
  const contextQuery = useQuery({
    queryKey: ['clinical-assistant-context', patientId],
    queryFn: () => getPatientClinicalContext(patientId),
    enabled: Boolean(patientId),
    staleTime: 30_000,
  })

  // 2. Fetch Active Assistant Session for this patient
  const sessionsQuery = useQuery({
    queryKey: ['clinical-assistant-sessions', patientId],
    queryFn: () => getAssistantSessions(patientId),
    enabled: Boolean(patientId),
    select: (sessions) => sessions[0] || null,
  })

  const currentSession: AssistantSession | null = sessionsQuery.data || null
  const currentMessages: AssistantMessage[] = currentSession?.messages || []
  const sessionId = activeSessionId || currentSession?.id

  // Optimistic view: show the user's in-flight questions immediately so the
  // conversation never feels stuck while the model is generating.
  const optimisticMessages: AssistantMessage[] = pendingMessages.map((text, index) => ({
    id: `pending-${index}-${text.length}`,
    role: 'user',
    content: text,
    validation_passed: true,
    created_at: new Date().toISOString(),
  }))
  const messages = [...currentMessages, ...optimisticMessages]

  // 3. Send Message Mutation
  const sendMutation = useMutation({
    mutationFn: (messageText: string) => sendChatMessage(patientId, messageText, sessionId),
    onMutate: (messageText) => {
      setPendingMessages((prev) => [...prev, messageText])
    },
    onSuccess: (data) => {
      setActiveSessionId(data.session_id)
      queryClient.invalidateQueries({ queryKey: ['clinical-assistant-sessions', patientId] })
      queryClient.invalidateQueries({ queryKey: ['clinical-assistant-context', patientId] })
    },
    onSettled: () => {
      // Remove the oldest pending message whether it succeeded (the refetched
      // session now contains it) or failed (the error alert explains why).
      setPendingMessages((prev) => prev.slice(1))
    },
  })

  // 4. Clear Session Mutation
  const clearMutation = useMutation({
    mutationFn: () => {
      if (!sessionId) return Promise.resolve()
      return clearAssistantSession(sessionId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clinical-assistant-sessions', patientId] })
    },
  })

  const suggestedPrompts =
    userRole === 'PATIENT_GUARD'
      ? GUARDIAN_SUGGESTED_PROMPTS
      : userRole === 'NURSE'
        ? NURSE_SUGGESTED_PROMPTS
        : DOCTOR_SUGGESTED_PROMPTS

  return {
    patientId,
    userRole,
    context: contextQuery.data || null,
    isContextLoading: contextQuery.isPending,
    messages,
    isMessagesLoading: sessionsQuery.isPending,
    sendMessage: (text: string) => sendMutation.mutate(text),
    isSending: sendMutation.isPending,
    sendError: sendMutation.error,
    clearSession: () => clearMutation.mutate(),
    isClearing: clearMutation.isPending,
    suggestedPrompts,
  }
}
