import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

/**
 * Stops one thrown render error from blanking the whole app.
 * Does not catch event-handler or async errors — those are handled at the call site.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('render error', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="panel panel-error" role="alert">
          <strong>Something broke while rendering this page.</strong>
          <p>Reload to try again.</p>
        </div>
      )
    }
    return this.props.children
  }
}
