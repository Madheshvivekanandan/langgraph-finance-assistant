import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  fetchCategories,
  fetchCategorySummary,
  fetchMonthlySummary,
  fetchStatements,
  fetchTransactions,
  setTransactionCategory,
} from '../api/financeApi'
import type { Category } from '../interfaces/category'
import type { Statement } from '../interfaces/statement'
import type { CategorySummaryList, MonthSummary } from '../interfaces/summary'
import type { Transaction } from '../interfaces/transaction'

type LoadStatus = 'loading' | 'ready' | 'error'

function describe(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Could not reach the server. Is the backend running?'
}

/** Owns all dashboard and transaction data, plus the active filters. */
export function useFinanceData() {
  const [statements, setStatements] = useState<Statement[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [months, setMonths] = useState<MonthSummary[]>([])
  const [categorySummary, setCategorySummary] = useState<CategorySummaryList | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [nextToken, setNextToken] = useState<string | undefined>(undefined)
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [savingIds, setSavingIds] = useState<ReadonlySet<number>>(new Set())
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  /** Data that does not depend on the active filters. */
  const loadUnfiltered = useCallback(async (isStale?: () => boolean) => {
    try {
      const [statementList, categoryList, monthList] = await Promise.all([
        fetchStatements(),
        fetchCategories(),
        fetchMonthlySummary(),
      ])
      if (isStale?.()) return
      setStatements(statementList.items)
      setCategories(categoryList.items)
      setMonths(monthList.items)
    } catch (error) {
      if (isStale?.()) return
      setErrorMessage(describe(error))
      setStatus('error')
    }
  }, [])

  /** Data that changes whenever the month or category filter changes. */
  const loadFiltered = useCallback(
    async (month: string | null, category: string | null, isStale?: () => boolean) => {
      try {
        const [summary, page] = await Promise.all([
          fetchCategorySummary(month),
          fetchTransactions({ month, category }),
        ])
        if (isStale?.()) return
        setCategorySummary(summary)
        setTransactions(page.items)
        setNextToken(page.next)
        setStatus('ready')
      } catch (error) {
        if (isStale?.()) return
        setErrorMessage(describe(error))
        setStatus('error')
      }
    },
    [],
  )

  useEffect(() => {
    let cancelled = false
    async function load(): Promise<void> {
      await loadUnfiltered(() => cancelled)
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [loadUnfiltered])

  useEffect(() => {
    let cancelled = false
    async function load(): Promise<void> {
      await loadFiltered(selectedMonth, selectedCategory, () => cancelled)
    }
    void load()
    return () => {
      // Stops a slow response for old filters overwriting newer results.
      cancelled = true
    }
  }, [loadFiltered, selectedMonth, selectedCategory])

  const reload = useCallback(async () => {
    await Promise.all([
      loadUnfiltered(),
      loadFiltered(selectedMonth, selectedCategory),
    ])
  }, [loadUnfiltered, loadFiltered, selectedMonth, selectedCategory])

  const loadMore = useCallback(async () => {
    if (!nextToken || isLoadingMore) return
    setIsLoadingMore(true)
    try {
      const page = await fetchTransactions(
        { month: selectedMonth, category: selectedCategory },
        nextToken,
      )
      setTransactions((previous) => [...previous, ...page.items])
      setNextToken(page.next)
    } catch (error) {
      setErrorMessage(describe(error))
    } finally {
      setIsLoadingMore(false)
    }
  }, [nextToken, isLoadingMore, selectedMonth, selectedCategory])

  const updateCategory = useCallback(
    async (transactionId: number, category: string) => {
      setSavingIds((previous) => new Set(previous).add(transactionId))
      try {
        const updated = await setTransactionCategory(transactionId, category)
        setTransactions((previous) =>
          previous.map((item) => (item.id === transactionId ? updated : item)),
        )
        // Recategorizing changes the breakdown, so the charts must catch up.
        await Promise.all([
          fetchCategorySummary(selectedMonth).then(setCategorySummary),
          fetchMonthlySummary().then((list) => setMonths(list.items)),
        ])
      } catch (error) {
        setErrorMessage(describe(error))
      } finally {
        setSavingIds((previous) => {
          const next = new Set(previous)
          next.delete(transactionId)
          return next
        })
      }
    },
    [selectedMonth],
  )

  return {
    statements,
    categories,
    months,
    categorySummary,
    transactions,
    selectedMonth,
    setSelectedMonth,
    selectedCategory,
    setSelectedCategory,
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
