import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchStatements, fetchTransactions } from '../api/financeApi'
import type { Statement } from '../interfaces/statement'
import type { Transaction } from '../interfaces/transaction'

type LoadStatus = 'loading' | 'ready' | 'error'

function describe(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Could not reach the server. Is the backend running?'
}

/** Owns all statement and transaction data for the page, plus its load states. */
export function useFinanceData() {
  const [statements, setStatements] = useState<Statement[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [nextToken, setNextToken] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  const reload = useCallback(async (isStale?: () => boolean) => {
    try {
      // Independent requests, so they go in parallel rather than one after the other.
      const [statementList, firstPage] = await Promise.all([
        fetchStatements(),
        fetchTransactions(),
      ])
      if (isStale?.()) return
      setStatements(statementList.items)
      setTransactions(firstPage.items)
      setNextToken(firstPage.next)
      setStatus('ready')
    } catch (error) {
      if (isStale?.()) return
      setErrorMessage(describe(error))
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    // Declared inline so every setState is clearly behind an await: this effect
    // synchronizes with an external system (the API), it does not derive state.
    async function loadInitialData(): Promise<void> {
      await reload(() => cancelled)
    }
    void loadInitialData()
    return () => {
      // Stops a slow first response from overwriting newer state after unmount.
      cancelled = true
    }
  }, [reload])

  const loadMore = useCallback(async () => {
    if (!nextToken || isLoadingMore) return
    setIsLoadingMore(true)
    try {
      const page = await fetchTransactions(nextToken)
      setTransactions((previous) => [...previous, ...page.items])
      setNextToken(page.next)
    } catch (error) {
      setErrorMessage(describe(error))
    } finally {
      setIsLoadingMore(false)
    }
  }, [nextToken, isLoadingMore])

  return {
    statements,
    transactions,
    status,
    errorMessage,
    hasMore: nextToken !== undefined,
    isLoadingMore,
    loadMore,
    reload,
  }
}
