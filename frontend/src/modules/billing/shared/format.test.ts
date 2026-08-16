import { describe, expect, it } from 'vitest'

import { formatMoney } from './format'

describe('formatMoney', () => {
  it('always includes the invoice currency code', () => {
    expect(formatMoney('1250.50', 'XAF')).toContain('XAF')
    expect(formatMoney('1250.50', 'USD')).toContain('USD')
  })
})
