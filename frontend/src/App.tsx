import { useEffect, useState } from 'react'
import './App.css'

type BackendHealth =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok' }

function App() {
  const [backendHealth, setBackendHealth] = useState<BackendHealth>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    async function checkBackend() {
      try {
        const response = await fetch('/api/v1/health', { signal: controller.signal })
        if (!response.ok) {
          setBackendHealth({ status: 'error', message: `backend replied ${response.status}` })
          return
        }
        setBackendHealth({ status: 'ok' })
      } catch (error) {
        if (controller.signal.aborted) return
        setBackendHealth({ status: 'error', message: 'backend unreachable' })
        console.error('health check failed', error)
      }
    }

    void checkBackend()
    return () => controller.abort()
  }, [])

  return (
    <main className="app">
      <h1>My Finance</h1>
      <p>Upload bank statements, see where the money goes, and ask questions about it.</p>
      <p role="status">
        Backend:{' '}
        {backendHealth.status === 'loading' && <span>checking…</span>}
        {backendHealth.status === 'ok' && <span className="health-ok">connected</span>}
        {backendHealth.status === 'error' && (
          <span className="health-error">{backendHealth.message}</span>
        )}
      </p>
    </main>
  )
}

export default App
