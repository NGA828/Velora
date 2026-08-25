import { BrainCircuit, ShieldCheck, User } from 'lucide-react'
import type { AssistantMessage } from '../types'

interface Props {
  message: AssistantMessage
  userRole?: string
}

export function ChatMessageBubble({ message, userRole }: Props) {
  const isUser = message.role === 'user'
  const timeStr = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <article className={`assistant-bubble ${isUser ? 'assistant-bubble--user' : 'assistant-bubble--assistant'}`}>
      <div className="assistant-bubble__avatar" aria-hidden="true">
        {isUser ? <User size={16} /> : <BrainCircuit size={16} />}
      </div>

      <div className="assistant-bubble__content">
        <header className="assistant-bubble__header">
          <strong>
            {isUser
              ? userRole === 'DOCTOR'
                ? 'Doctor (You)'
                : userRole === 'NURSE'
                  ? 'Nurse (You)'
                  : userRole === 'PATIENT_GUARD'
                    ? 'Patient Guard (You)'
                    : 'You'
              : 'Clinical Information Assistant'}
          </strong>
          <span className="assistant-bubble__time">{timeStr}</span>
        </header>

        <div className="assistant-bubble__body">
          {message.content.split('\n\n').map((paragraph, idx) => (
            <p key={idx}>{paragraph}</p>
          ))}
        </div>

        {!isUser && (
          <footer className="assistant-bubble__footer">
            <span className="assistant-bubble__source">
              <ShieldCheck size={13} /> Grounded in Velora Clinical Context
            </span>
          </footer>
        )}
      </div>
    </article>
  )
}
