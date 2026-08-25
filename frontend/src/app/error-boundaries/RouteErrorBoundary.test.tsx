import { cleanup, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RouteErrorBoundary } from './RouteErrorBoundary'
import { isStaleAssetError, STALE_ASSET_RELOAD_GUARD } from './stale-asset'

const STALE_MODULE_ERROR =
  'Failed to fetch dynamically imported module: https://hospital.example.org/assets/LoginPage-BR26Oni1.js'
const STALE_PRELOAD_ERROR = 'Unable to preload CSS for /assets/index-CA3T5Yfh.css'

const STALE_MESSAGES = [
  STALE_MODULE_ERROR,
  'error loading dynamically imported module',
  'Importing a module script failed.',
  STALE_PRELOAD_ERROR,
]

/** A route whose chunk the current deployment no longer serves. */
const routerFor = (message: string) =>
  createMemoryRouter([
    {
      errorElement: <RouteErrorBoundary />,
      children: [
        {
          path: '/',
          lazy: async () => {
            throw new Error(message)
          },
        },
      ],
    },
  ])

describe('isStaleAssetError', () => {
  it.each(STALE_MESSAGES)('recognises "%s" as a stale asset failure', (message) => {
    expect(isStaleAssetError(new Error(message))).toBe(true)
  })

  it('does not misclassify ordinary runtime errors as stale assets', () => {
    expect(isStaleAssetError(new Error("Cannot read properties of undefined (reading 'id')"))).toBe(false)
    expect(isStaleAssetError(undefined)).toBe(false)
  })
})

describe('RouteErrorBoundary', () => {
  const originalLocation = window.location
  let reload: ReturnType<typeof vi.fn>

  beforeEach(() => {
    sessionStorage.clear()
    reload = vi.fn()
    // jsdom's Location.prototype.reload is non-configurable, so replace the
    // whole object instead of spying on the method.
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: { href: 'http://localhost/', reload, replace: vi.fn() },
    })
  })

  afterEach(() => {
    // Vitest runs without `globals`, so Testing Library's automatic cleanup does
    // not run. Unmount explicitly or a stale boundary from the previous test
    // flushes its reload effect into this one.
    cleanup()
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: originalLocation,
    })
  })

  it('reloads once and explains the update instead of rendering a blank screen', async () => {
    render(<RouterProvider router={routerFor(STALE_MODULE_ERROR)} />)

    expect(await screen.findByRole('heading', { name: 'Velora was just updated' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load the latest version' })).toBeInTheDocument()
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('does not reload again once the guard is set, so it cannot loop', async () => {
    sessionStorage.setItem(STALE_ASSET_RELOAD_GUARD, '1')

    render(<RouterProvider router={routerFor(STALE_PRELOAD_ERROR)} />)

    expect(await screen.findByRole('heading', { name: 'Velora was just updated' })).toBeInTheDocument()
    expect(reload).not.toHaveBeenCalled()
  })

  it('reports genuine application errors with their message', async () => {
    render(<RouterProvider router={routerFor('Cannot read properties of undefined')} />)

    expect(await screen.findByRole('heading', { name: 'This page could not be displayed' })).toBeInTheDocument()
    expect(screen.getByText('Cannot read properties of undefined')).toBeInTheDocument()
    expect(reload).not.toHaveBeenCalled()
  })
})
