import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders a textual status so color is not the only signal', () => {
    render(<StatusBadge status="UNAVAILABLE" />)
    expect(screen.getByText('Unavailable')).toHaveClass('status-badge--critical')
  })
})
