import { describe, expect, it } from 'vitest'

import { changePasswordSchema, invitationSchema, loginSchema } from './auth-schemas'

describe('authentication schemas', () => {
  it('rejects an invalid email address', () => {
    const result = loginSchema.safeParse({ email: 'not-an-email', password: 'password' })
    expect(result.success).toBe(false)
  })

  it('requires invitation passwords to match', () => {
    const result = invitationSchema.safeParse({
      first_name: 'Amara',
      last_name: 'Nwosu',
      password: 'a-long-password-one',
      confirm_password: 'a-long-password-two',
    })
    expect(result.success).toBe(false)
  })

  it('accepts a valid password change payload', () => {
    const result = changePasswordSchema.safeParse({
      old_password: 'current-password',
      new_password: 'new-secure-password',
      confirm_password: 'new-secure-password',
    })
    expect(result.success).toBe(true)
  })
})
