import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchGraphTopology } from '../api/financeApi'
import type { GraphTopology } from '../interfaces/graphTopology'

type LoadStatus = 'loading' | 'ready' | 'error'

function describe(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Could not reach the server. Is the backend running?'
}

/** Fetches one graph's topology on mount. Modelled on `useStatementReview`. */
export function useGraphTopology(name: string) {
  const [topology, setTopology] = useState<GraphTopology | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorMessage, setErrorMessage] = useState('')

  const load = useCallback(async (graphName: string, isStale?: () => boolean) => {
    setStatus('loading')
    try {
      const data = await fetchGraphTopology(graphName)
      if (isStale?.()) return
      setTopology(data)
      setStatus('ready')
    } catch (error) {
      if (isStale?.()) return
      setErrorMessage(describe(error))
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function run(): Promise<void> {
      await load(name, () => cancelled)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [load, name])

  return { status, topology, errorMessage }
}
