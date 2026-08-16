import { describe, expect, it } from 'vitest'

import { AppApiError, firstFieldError } from './errors'

describe('API errors', () => {
  it('extracts the first backend field error', () => {
    const error = new AppApiError({
      message: 'Validation failed',
      status: 400,
      fields: { email: ['An account already exists.'] },
    })

    expect(firstFieldError(error, 'email')).toBe('An account already exists.')
  })
})
