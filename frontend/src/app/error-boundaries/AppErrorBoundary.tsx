import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Top-level error boundary that catches unhandled render errors (e.g. a stale
 * cached chunk referencing a missing export) and shows a recovery UI instead
 * of a blank screen.
 */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('AppErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="standalone-state">
          <h1>Something went wrong</h1>
          <p>{this.state.error.message}</p>
          <button
            className="button button--primary"
            onClick={() => window.location.reload()}
          >
            Reload the page
          </button>
        </main>
      )
    }
    return this.props.children
  }
}
