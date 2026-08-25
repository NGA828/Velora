import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'

import { AppProviders } from './app/providers/AppProviders'
import { createAppRouter } from './app/router'
import './shared/styles/tokens.css'
import './shared/styles/globals.css'

const container = document.getElementById('root')!

let router = createAppRouter()
const root = createRoot(container)

function render() {
  root.render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  )
}

render()

if (import.meta.hot) {
  // createBrowserRouter caches the resolved Component for each route, so a
  // Fast-Refresh update to a route module never reaches the screen. Rebuilding
  // the router on every hot update re-resolves the lazy route modules, which
  // makes edits show up without a manual hard refresh.
  import.meta.hot.on('vite:afterUpdate', () => {
    router = createAppRouter()
    render()
  })
}
