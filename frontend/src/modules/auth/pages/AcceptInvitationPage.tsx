import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'

import { AuthLayout } from '../../../app/layouts/AuthLayout'
import { AppApiError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { FormField, PasswordField } from '../../../shared/ui/forms/FormField'
import { acceptInvitation } from '../api/auth-api'
import { sessionQueryKey } from '../hooks/use-session'
import { invitationSchema } from '../schemas/auth-schemas'
import type { InvitationFormValues } from '../schemas/auth-schemas'

function invitationTokenFromHash(): string {
  return new URLSearchParams(window.location.hash.slice(1)).get('token') ?? ''
}

export function AcceptInvitationPage() {
  const [token] = useState(invitationTokenFromHash)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mutation = useMutation({ mutationFn: acceptInvitation })
  const form = useForm<InvitationFormValues>({
    resolver: zodResolver(invitationSchema),
    defaultValues: { first_name: '', last_name: '', phone: '', password: '', confirm_password: '' },
  })

  useEffect(() => {
    document.title = 'Accept invitation · Velora'
    if (window.location.hash) window.history.replaceState(null, '', window.location.pathname)
  }, [])

  const onSubmit = form.handleSubmit(async (values) => {
    mutation.reset()
    try {
      const session = await mutation.mutateAsync({ token, ...values })
      queryClient.setQueryData(sessionQueryKey, session)
      navigate('/', { replace: true })
    } catch {
      form.setFocus('first_name')
    }
  })

  const apiError = mutation.error instanceof AppApiError ? mutation.error : undefined

  return (
    <AuthLayout>
      <div className="auth-form-card auth-form-card--wide">
        <div className="auth-form-card__heading">
          <p className="eyebrow">Account invitation</p>
          <h2>Set up your secure access</h2>
          <p>Confirm your identity details and choose a private password.</p>
        </div>

        {!token ? (
          <Alert tone="critical" title="Invitation link unavailable">
            This link is incomplete. Open the full invitation from your email or ask the sender for
            a new invitation.
          </Alert>
        ) : (
          <>
            {apiError && (
              <Alert tone="critical" title="Account setup was not completed">
                {apiError.message}
              </Alert>
            )}
            <form onSubmit={onSubmit} noValidate>
              <div className="form-grid">
                <FormField
                  label="First name"
                  autoComplete="given-name"
                  autoFocus
                  error={form.formState.errors.first_name?.message}
                  {...form.register('first_name')}
                />
                <FormField
                  label="Last name"
                  autoComplete="family-name"
                  error={form.formState.errors.last_name?.message}
                  {...form.register('last_name')}
                />
              </div>
              <FormField
                label="Telephone (optional)"
                type="tel"
                autoComplete="tel"
                error={form.formState.errors.phone?.message}
                {...form.register('phone')}
              />
              <PasswordField
                label="Password"
                autoComplete="new-password"
                helperText="Use at least 12 characters. Avoid personal or hospital details."
                error={form.formState.errors.password?.message}
                {...form.register('password')}
              />
              <PasswordField
                label="Confirm password"
                autoComplete="new-password"
                error={form.formState.errors.confirm_password?.message}
                {...form.register('confirm_password')}
              />
              <Button type="submit" fullWidth isLoading={mutation.isPending}>
                Create secure account
              </Button>
            </form>
          </>
        )}
        <p className="auth-form-card__help">
          Already set up? <Link to="/login">Return to sign in</Link>
        </p>
      </div>
    </AuthLayout>
  )
}
