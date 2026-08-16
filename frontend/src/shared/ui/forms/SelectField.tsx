import { forwardRef, useId } from 'react'
import type { SelectHTMLAttributes } from 'react'

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
  helperText?: string
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(function SelectField(
  { label, error, helperText, id: suppliedId, children, ...props },
  ref,
) {
  const generatedId = useId()
  const id = suppliedId ?? generatedId
  return (
    <div className={`form-field ${error ? 'form-field--error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <select ref={ref} id={id} aria-invalid={Boolean(error)} {...props}>{children}</select>
      {error ? <span className="form-field__error" role="alert">{error}</span> : helperText ? <span className="form-field__helper">{helperText}</span> : null}
    </div>
  )
})
