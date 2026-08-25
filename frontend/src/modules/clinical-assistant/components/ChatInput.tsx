import { ArrowUp, Loader2 } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

interface Props {
  onSend: (message: string) => void
  disabled?: boolean
  isLoading?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, isLoading, placeholder }: Props) {
  const [text, setText] = useState('')

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled || isLoading) return
    onSend(trimmed)
    setText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="assistant-input-wrap">
      <textarea
        className="assistant-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Ask a clinical question about this patient... (Enter to send)'}
        rows={2}
        disabled={disabled || isLoading}
        maxLength={3000}
      />
      <div className="assistant-input-footer">
        <span className="assistant-input-hint">Shift + Enter for new line</span>
        <button
          type="button"
          className="assistant-send-btn"
          onClick={handleSend}
          disabled={!text.trim() || disabled || isLoading}
          aria-label="Send message"
        >
          {isLoading ? <Loader2 size={16} className="spin" /> : <ArrowUp size={16} />}
        </button>
      </div>
    </div>
  )
}
