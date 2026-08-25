/**
 * Detects the failure a stale `index.html` produces after a deployment: the
 * cached document still points at content-hashed chunks the new release
 * removed, so the dynamic import rejects with one of these messages.
 *
 * Kept separate from the component so `RouteErrorBoundary.tsx` exports only
 * components (Fast Refresh requires it) and the matching stays unit-testable.
 */
const STALE_ASSET_PATTERNS = [
  /failed to fetch dynamically imported module/i,
  /error loading dynamically imported module/i,
  /importing a module script failed/i,
  /unable to preload css/i,
  /error loading css file/i,
]

export function isStaleAssetError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === 'AbortError') return false
  const message = error instanceof Error ? error.message : String(error ?? '')
  return STALE_ASSET_PATTERNS.some((pattern) => pattern.test(message))
}

/** Set before an automatic reload so a persistent failure cannot loop. */
export const STALE_ASSET_RELOAD_GUARD = 'velora:stale-asset-reload'
