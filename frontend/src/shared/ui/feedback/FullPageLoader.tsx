import { LoaderCircle } from 'lucide-react'

import { Brand } from '../navigation/Brand'

export function FullPageLoader() {
  return (
    <main className="page-loader" aria-busy="true" aria-label="Loading secure workspace">
      <Brand />
      <LoaderCircle className="page-loader__spinner" size={30} aria-hidden="true" />
      <p>Opening your secure workspace…</p>
    </main>
  )
}
