import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Modal } from './Modal'

describe('Modal', () => {
  it('closes with Escape and labels the dialog', () => {
    const onClose = vi.fn()
    render(<Modal open title="Add department" onClose={onClose}><p>Form content</p></Modal>)

    expect(screen.getByRole('dialog', { name: 'Add department' })).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })
})
