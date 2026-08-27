import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { AppProviders } from '../../app/providers/AppProviders'
import { LandingPage } from './LandingPage'

afterEach(cleanup)

function renderLanding() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <AppProviders>
        <LandingPage />
      </AppProviders>
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  it('renders the hero with a login call to action', () => {
    renderLanding()

    expect(screen.getAllByRole('link', { name: /log in/i }).length).toBeGreaterThan(0)
    expect(screen.getByText(/ICU-grade clarity for every patient/i)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /monitoring dashboard/i })).toBeInTheDocument()
  })

  it('renders the platform, assistant, workflow and testimonial sections', () => {
    renderLanding()

    expect(screen.getAllByText('ICU Recommendation Engine').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/explains — it never decides/i).length).toBeGreaterThan(0)
    expect(screen.getByText('Record vitals at the bedside')).toBeInTheDocument()
    expect(screen.getByText('What the care team says')).toBeInTheDocument()
  })

  it('uses generated landing imagery', () => {
    renderLanding()

    const images = screen.getAllByRole('img')
    const sources = images.map((img) => img.getAttribute('src'))
    expect(sources.some((src) => src && src.includes('hero-dashboard'))).toBe(true)
    expect(sources.some((src) => src && src.includes('icu-monitoring'))).toBe(true)
    expect(sources.some((src) => src && src.includes('guardian'))).toBe(true)
    expect(sources.some((src) => src && src.includes('care-team'))).toBe(true)
  })
})
