import { forwardRef, useId } from 'react'
import type { TextareaHTMLAttributes } from 'react'

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  error?: string
  helperText?: string
}

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>(
  function TextAreaField({ label, error, helperText, id: suppliedId, ...props }, ref) {
    const generatedId = useId()
    const id = suppliedId ?? generatedId
    return (
      <div className={`form-field ${error ? 'form-field--error' : ''}`}>
        <label htmlFor={id}>{label}</label>
        <textarea ref={ref} id={id} aria-invalid={Boolean(error)} {...props} />
        {error ? <span className="form-field__error" role="alert">{error}</span> : helperText ? <span className="form-field__helper">{helperText}</span> : null}
      </div>
    )
  },
)
