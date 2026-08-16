import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router-dom'

import { AuthLayout } from '../../../app/layouts/AuthLayout'
import { AppApiError, firstFieldError } from '../../../shared/api/errors'
import { Button } from '../../../shared/ui/actions/Button'
import { Alert } from '../../../shared/ui/feedback/Alert'
import { FormField, PasswordField } from '../../../shared/ui/forms/FormField'
import { login } from '../api/auth-api'
import { sessionQueryKey } from '../hooks/use-session'
import { loginSchema } from '../schemas/auth-schemas'
import type { LoginFormValues } from '../schemas/auth-schemas'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })
  const mutation = useMutation({ mutationFn: login })

  useEffect(() => {
    document.title = 'Sign in · Velora'
  }, [])

  const onSubmit = form.handleSubmit(async (values) => {
    mutation.reset()
    try {
      const session = await mutation.mutateAsync(values)
      queryClient.setQueryData(sessionQueryKey, session)
      const requestedPath = (location.state as { from?: string } | null)?.from
      navigate(session.user.must_change_password ? '/change-password' : requestedPath || '/', {
        replace: true,
      })
    } catch {
      form.setFocus('email')
    }
  })

  const apiError = mutation.error instanceof AppApiError ? mutation.error : undefined

  return (
    <AuthLayout>
      <div className="auth-form-card">
        <div className="auth-form-card__heading">
          <p className="eyebrow">Secure access</p>
          <h2>Welcome back</h2>
          <p>Use the account provided by your hospital.</p>
        </div>

        {apiError && (
          <Alert tone="critical" title="Sign in was not completed">
            {apiError.message}
            {apiError.requestId && <small>Reference: {apiError.requestId}</small>}
          </Alert>
        )}

        <form onSubmit={onSubmit} noValidate>
          <FormField
            label="Email address"
            type="email"
            autoComplete="username"
            autoFocus
            error={form.formState.errors.email?.message ?? firstFieldError(apiError, 'email')}
            {...form.register('email')}
          />
          <PasswordField
            label="Password"
            autoComplete="current-password"
            error={form.formState.errors.password?.message ?? firstFieldError(apiError!, 'password')}
            {...form.register('password')}
          />
          <Button type="submit" fullWidth isLoading={mutation.isPending}>
            Sign in securely
          </Button>
        </form>

        <p className="auth-form-card__help">
          Cannot access your account? Contact your hospital administrator. For your safety, Velora
          never asks for a password by email.
        </p>
      </div>
    </AuthLayout>
  )
}
