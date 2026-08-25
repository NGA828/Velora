import { BrainCircuit, Sparkles, Trash2, X } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { useClinicalAssistant } from '../use-clinical-assistant'
import { ChatInput } from './ChatInput'
import { ChatMessageBubble } from './ChatMessageBubble'
import { ClinicalContextBadge } from './ClinicalContextBadge'
import { SafetyNotice } from './SafetyNotice'

interface Props {
  open: boolean
  onClose: () => void
  patientId: string
  patientName?: string
  medicalRecordNumber?: string
  initialPrompt?: string
}

export function ClinicalAssistantDrawer({
  open,
  onClose,
  patientId,
  patientName,
  medicalRecordNumber,
  initialPrompt,
}: Props) {
  const {
    userRole,
    context,
    isContextLoading,
    messages,
    isMessagesLoading,
    sendMessage,
    isSending,
    sendError,
    clearSession,
    isClearing,
    suggestedPrompts,
  } = useClinicalAssistant(patientId)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initialPromptSent = useRef(false)

  // Scroll to bottom on new messages
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isSending, open])

  // Handle initial prompt if passed
  useEffect(() => {
    if (open && initialPrompt && !initialPromptSent.current && messages.length === 0 && !isMessagesLoading) {
      initialPromptSent.current = true
      sendMessage(initialPrompt)
    }
  }, [open, initialPrompt, messages.length, isMessagesLoading, sendMessage])

  if (!open) return null

  const isGuardian = userRole === 'PATIENT_GUARD'
  const displayName = patientName || context?.patient.full_name || context?.patient.first_name || 'Patient'
  const displayMrn = medicalRecordNumber || context?.patient.medical_record_number || ''

  return (
    <div className="assistant-drawer-layer" role="presentation" onMouseDown={(e) => {
      if (e.target === e.currentTarget) onClose()
    }}>
      <aside
        className="assistant-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Clinical Decision Support Assistant"
      >
        {/* Drawer Header */}
        <header className="assistant-drawer__header">
          <div className="assistant-drawer__title-wrap">
            <span className="assistant-drawer__icon">
              <BrainCircuit size={20} />
            </span>
            <div>
              <h2>{isGuardian ? 'Care Information Assistant' : 'Clinical Assistant'}</h2>
              <p>
                {displayName} {displayMrn ? `· ${displayMrn}` : ''}
              </p>
            </div>
          </div>
          <div className="assistant-drawer__actions">
            {messages.length > 0 && (
              <button
                type="button"
                className="icon-button icon-button--subtle"
                title="Clear conversation"
                onClick={() => clearSession()}
                disabled={isClearing || isSending}
                aria-label="Clear conversation"
              >
                <Trash2 size={16} />
              </button>
            )}
            <button
              type="button"
              className="icon-button"
              onClick={onClose}
              aria-label="Close assistant drawer"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* Clinical Context & Safety Notice */}
        <div className="assistant-drawer__context-section">
          <ClinicalContextBadge context={context} loading={isContextLoading} />
          <SafetyNotice isGuardian={isGuardian} />
        </div>

        {/* Message Thread */}
        <div className="assistant-drawer__thread">
          {isMessagesLoading ? (
            <SectionLoader label="Loading session..." />
          ) : messages.length === 0 ? (
            <div className="assistant-empty">
              <div className="assistant-empty__icon">
                <Sparkles size={28} />
              </div>
              <h3>
                {isGuardian
                  ? 'Ask about your loved one’s care'
                  : 'Clinical Decision Support Assistant'}
              </h3>
              <p>
                {isGuardian
                  ? 'Get plain-language explanations of recorded vitals, care updates, and ICU evaluation status.'
                  : 'Query patient status, vital sign trends, triggered rule thresholds, and ICU recommendation rationale.'}
              </p>

              <div className="assistant-empty__prompts">
                <span className="assistant-empty__prompts-label">Suggested queries:</span>
                <div className="assistant-prompt-chips">
                  {suggestedPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="assistant-prompt-chip"
                      onClick={() => sendMessage(prompt)}
                      disabled={isSending}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="assistant-messages-list">
              {messages.map((msg) => (
                <ChatMessageBubble key={msg.id} message={msg} userRole={userRole} />
              ))}

              {isSending && (
                <article className="assistant-bubble assistant-bubble--assistant assistant-bubble--typing">
                  <div className="assistant-bubble__avatar">
                    <BrainCircuit size={16} />
                  </div>
                  <div className="assistant-bubble__content">
                    <div className="assistant-typing-indicator">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </article>
              )}

              {sendError && (
                <Alert tone="critical" title="Unable to send message">
                  {sendError instanceof Error ? sendError.message : 'Please try again.'}
                </Alert>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Footer */}
        <footer className="assistant-drawer__footer">
          {messages.length > 0 && suggestedPrompts.length > 0 && suggestedPrompts[0] && !isSending && (
            <div className="assistant-quick-actions">
              <button
                type="button"
                className="assistant-quick-chip"
                onClick={() => {
                  if (suggestedPrompts[0]) sendMessage(suggestedPrompts[0])
                }}
              >
                <Sparkles size={13} /> {suggestedPrompts[0]}
              </button>
            </div>
          )}
          <ChatInput
            onSend={(text) => sendMessage(text)}
            isLoading={isSending}
            placeholder={
              isGuardian
                ? 'Ask a question about the patient’s care...'
                : 'Ask about vitals, rule evaluations, ICU recommendation...'
            }
          />
        </footer>
      </aside>
    </div>
  )
}
