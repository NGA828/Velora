import { BrainCircuit, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Alert } from '../../../shared/ui/feedback/Alert'
import { SectionLoader } from '../../../shared/ui/feedback/SectionLoader'
import { useClinicalAssistant } from '../use-clinical-assistant'
import { ChatInput } from './ChatInput'
import { ChatMessageBubble } from './ChatMessageBubble'
import { ClinicalContextBadge } from './ClinicalContextBadge'
import { SafetyNotice } from './SafetyNotice'

interface Props {
  patientId: string
  patientName?: string
  medicalRecordNumber?: string
}

/**
 * Full-page variant of the Clinical Assistant chat. Uses the same building
 * blocks as the drawer but rendered as an embedded workspace panel.
 */
export function ClinicalAssistantPanel({ patientId, patientName, medicalRecordNumber }: Props) {
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages, isSending])

  const isGuardian = userRole === 'PATIENT_GUARD'
  const displayName = patientName || context?.patient.full_name || context?.patient.first_name || 'Patient'
  const displayMrn = medicalRecordNumber || context?.patient.medical_record_number || ''

  return (
    <section className="assistant-panel" aria-label="Clinical Decision Support Assistant">
      <header className="assistant-panel__header">
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
        </div>
      </header>

      <div className="assistant-drawer__context-section">
        <ClinicalContextBadge context={context} loading={isContextLoading} />
        <SafetyNotice isGuardian={isGuardian} />
      </div>

      <div className="assistant-panel__thread">
        {isMessagesLoading ? (
          <SectionLoader label="Loading session..." />
        ) : messages.length === 0 ? (
          <div className="assistant-empty">
            <div className="assistant-empty__icon">
              <Sparkles size={28} />
            </div>
            <h3>
              {isGuardian ? 'Ask about your loved one’s care' : 'Clinical Decision Support Assistant'}
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
            <div ref={messagesEndRef} />
          </div>
        )}

        {sendError && (
          <div className="assistant-error-wrap">
            <Alert tone="critical" title="Unable to send message">
              {sendError instanceof Error
                ? `${sendError.message} Your message was not delivered — please try again.`
                : 'Your message was not delivered — please try again.'}
            </Alert>
          </div>
        )}
      </div>

      <footer className="assistant-panel__footer">
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
    </section>
  )
}
