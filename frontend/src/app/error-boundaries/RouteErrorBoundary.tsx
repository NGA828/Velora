import { useEffect } from 'react'
import { isRouteErrorResponse, useRouteError } from 'react-router-dom'

import { Alert } from '../../shared/ui/feedback/Alert'
import { Button } from '../../shared/ui/actions/Button'
import { Brand } from '../../shared/ui/navigation/Brand'
import { isStaleAssetError, STALE_ASSET_RELOAD_GUARD } from './stale-asset'

/**
 * Catches route-level failures so a broken screen is never a silent blank page.
 *
 * When the cause is a chunk the current deployment no longer serves, we reload
 * once to pull a fresh `index.html`; if that did not help we say so and offer a
 * cache-bypassing load, because a plain reload can replay the same cached
 * document and land back here.
 */
function bypassCacheAndReload() {
  sessionStorage.removeItem(STALE_ASSET_RELOAD_GUARD)
  const url = new URL(window.location.href)
  url.searchParams.set('_r', String(Date.now()))
  window.location.replace(url.toString())
}

export function RouteErrorBoundary() {
  const error = useRouteError()
  const stale = isStaleAssetError(error)

  useEffect(() => {
    if (!stale || sessionStorage.getItem(STALE_ASSET_RELOAD_GUARD)) return
    sessionStorage.setItem(STALE_ASSET_RELOAD_GUARD, '1')
    window.location.reload()
  }, [stale])

  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : 'An unexpected error interrupted this page.'

  return (
    <main className="standalone-state">
      <Brand />
      <p className="eyebrow">{stale ? 'Update available' : 'Something went wrong'}</p>
      <h1>{stale ? 'Velora was just updated' : 'This page could not be displayed'}</h1>
      <Alert
        tone={stale ? 'information' : 'critical'}
        title={stale ? 'A newer version is installed' : 'We could not load this screen'}
      >
        {stale
          ? 'The workspace was updated while this tab was open, so the files your browser cached no longer exist on the server. Load the latest version to continue.'
          : detail}
      </Alert>
      <Button variant="primary" onClick={stale ? bypassCacheAndReload : () => window.location.reload()}>
        {stale ? 'Load the latest version' : 'Reload the workspace'}
      </Button>
    </main>
  )
}
