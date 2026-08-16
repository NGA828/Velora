import { forwardRef, useId, useState } from 'react'
import type { InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  helperText?: string
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(function FormField(
  { label, error, helperText, id: suppliedId, type = 'text', className = '', ...props },
  ref,
) {
  const generatedId = useId()
  const id = suppliedId ?? generatedId
  const helperId = helperText ? `${id}-helper` : undefined
  const errorId = error ? `${id}-error` : undefined

  return (
    <div className={`form-field ${error ? 'form-field--error' : ''} ${className}`}>
      <label htmlFor={id}>{label}</label>
      <input
        ref={ref}
        id={id}
        type={type}
        aria-invalid={Boolean(error)}
        aria-describedby={errorId ?? helperId}
        {...props}
      />
      {error ? (
        <span className="form-field__error" id={errorId} role="alert">
          {error}
        </span>
      ) : helperText ? (
        <span className="form-field__helper" id={helperId}>
          {helperText}
        </span>
      ) : null}
    </div>
  )
})

export const PasswordField = forwardRef<HTMLInputElement, FormFieldProps>(
  function PasswordField({ label, error, helperText, id: suppliedId, ...props }, ref) {
    const generatedId = useId()
    const id = suppliedId ?? generatedId
    const [visible, setVisible] = useState(false)
    const helperId = helperText ? `${id}-helper` : undefined
    const errorId = error ? `${id}-error` : undefined

    return (
      <div className={`form-field ${error ? 'form-field--error' : ''}`}>
        <label htmlFor={id}>{label}</label>
        <div className="form-field__password-wrap">
          <input
            ref={ref}
            id={id}
            type={visible ? 'text' : 'password'}
            aria-invalid={Boolean(error)}
            aria-describedby={errorId ?? helperId}
            {...props}
          />
          <button
            type="button"
            className="form-field__reveal"
            onClick={() => setVisible((current) => !current)}
            aria-label={visible ? 'Hide password' : 'Show password'}
          >
            {visible ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error ? (
          <span className="form-field__error" id={errorId} role="alert">
            {error}
          </span>
        ) : helperText ? (
          <span className="form-field__helper" id={helperId}>
            {helperText}
          </span>
        ) : null}
      </div>
    )
  },
)
