import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { AppApiError, firstFieldError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { PasswordField } from '../../../shared/ui/forms/FormField'
import { Brand } from '../../../shared/ui/navigation/Brand'
import { changePassword } from '../api/auth-api'
import { sessionQueryKey } from '../hooks/use-session'
import { changePasswordSchema } from '../schemas/auth-schemas'
import type { ChangePasswordFormValues } from '../schemas/auth-schemas'

export function ChangePasswordPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mutation = useMutation({ mutationFn: changePassword })
  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { old_password: '', new_password: '', confirm_password: '' },
  })

  useEffect(() => {
    document.title = 'Change password · Velora'
  }, [])

  const onSubmit = form.handleSubmit(async (values) => {
    mutation.reset()
    try {
      const session = await mutation.mutateAsync(values)
      queryClient.setQueryData(sessionQueryKey, session)
      navigate('/', { replace: true })
    } catch {
      form.setFocus('old_password')
    }
  })

  const apiError = mutation.error instanceof AppApiError ? mutation.error : undefined

  return (
    <main className="password-page">
      <Brand />
      <section className="password-card">
        <p className="eyebrow">Account protection</p>
        <h1>Choose a new password</h1>
        <p>Your hospital requires a private password before the workspace can be opened.</p>
        {apiError && <Alert tone="critical">{apiError.message}</Alert>}
        <form onSubmit={onSubmit} noValidate>
          <PasswordField
            label="Current password"
            autoComplete="current-password"
            error={form.formState.errors.old_password?.message ?? firstFieldError(apiError, 'old_password')}
            {...form.register('old_password')}
          />
          <PasswordField
            label="New password"
            autoComplete="new-password"
            helperText="Use at least 12 characters and avoid names or patient information."
            error={form.formState.errors.new_password?.message ?? firstFieldError(apiError!, 'new_password')}
            {...form.register('new_password')}
          />
          <PasswordField
            label="Confirm new password"
            autoComplete="new-password"
            error={form.formState.errors.confirm_password?.message}
            {...form.register('confirm_password')}
          />
          <Button type="submit" fullWidth isLoading={mutation.isPending}>
            Update password
          </Button>
        </form>
      </section>
    </main>
  )
}
