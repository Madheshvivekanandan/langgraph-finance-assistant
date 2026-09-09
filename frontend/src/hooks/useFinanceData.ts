import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  fetchCategories,
  fetchStatements,
  fetchTransactions,
  setTransactionCategory,
} from '../api/financeApi'
import type { Category } from '../interfaces/category'
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
  const [categories, setCategories] = useState<Category[]>([])
  const [savingIds, setSavingIds] = useState<ReadonlySet<number>>(new Set())
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [nextToken, setNextToken] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  const reload = useCallback(async (isStale?: () => boolean) => {
    try {
      // Independent requests, so they go in parallel rather than one after the other.
      const [statementList, firstPage, categoryList] = await Promise.all([
        fetchStatements(),
        fetchTransactions(),
        fetchCategories(),
      ])
      if (isStale?.()) return
      setStatements(statementList.items)
      setTransactions(firstPage.items)
      setNextToken(firstPage.next)
      setCategories(categoryList.items)
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

  const updateCategory = useCallback(async (transactionId: number, category: string) => {
    setSavingIds((previous) => new Set(previous).add(transactionId))
    try {
      const updated = await setTransactionCategory(transactionId, category)
      // Replace only the edited row; a full reload would lose the loaded pages.
      setTransactions((previous) =>
        previous.map((item) => (item.id === transactionId ? updated : item)),
      )
    } catch (error) {
      setErrorMessage(describe(error))
    } finally {
      setSavingIds((previous) => {
        const next = new Set(previous)
        next.delete(transactionId)
        return next
      })
    }
  }, [])

  return {
    statements,
    transactions,
    categories,
    savingIds,
    updateCategory,
    status,
    errorMessage,
    hasMore: nextToken !== undefined,
    isLoadingMore,
    loadMore,
    reload,
  }
}
