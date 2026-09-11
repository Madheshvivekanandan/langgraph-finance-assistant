import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  discardStatement,
  getStatementReview,
  submitStatementReview,
} from '../api/financeApi'
import type { StatementReview } from '../interfaces/statementReview'

type LoadStatus = 'loading' | 'ready' | 'error'

function describe(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Could not reach the server. Is the backend running?'
}

/** Owns the pending rows for one AWAITING_REVIEW statement and their edits. */
export function useStatementReview(statementId: number | null, onResolved: () => void) {
  const [review, setReview] = useState<StatementReview | null>(null)
  const [choices, setChoices] = useState<Record<number, string>>({})
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const load = useCallback(async (id: number, isStale?: () => boolean) => {
    setStatus('loading')
    try {
      const data = await getStatementReview(id)
      if (isStale?.()) return
      setReview(data)
      // Every row starts seeded to the model's own suggestion.
      setChoices(
        Object.fromEntries(data.items.map((item) => [item.index, item.suggested_category])),
      )
      setStatus('ready')
    } catch (error) {
      if (isStale?.()) return
      setErrorMessage(describe(error))
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    if (statementId === null) return
    const id = statementId
    let cancelled = false
    async function run(): Promise<void> {
      await load(id, () => cancelled)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [load, statementId])

  const setChoice = useCallback((index: number, category: string) => {
    setChoices((previous) => ({ ...previous, [index]: category }))
  }, [])

  const submit = useCallback(async () => {
    if (statementId === null || !review) return
    setIsSubmitting(true)
    try {
      // Rows left at the model's suggestion need no decision at all - an
      // "approve everything" submission is an empty list.
      const decisions = review.items
        .filter((item) => choices[item.index] !== item.suggested_category)
        .map((item) => ({ index: item.index, category: choices[item.index] }))
      await submitStatementReview(statementId, decisions)
      setReview(null)
      onResolved()
    } catch (error) {
      setErrorMessage(describe(error))
    } finally {
      setIsSubmitting(false)
    }
  }, [statementId, review, choices, onResolved])

  const discard = useCallback(async () => {
    // Gated on statementId only (not `review`), so this also works from the
    // `error` branch, where `review` is already null.
    if (statementId === null) return
    setIsSubmitting(true)
    try {
      await discardStatement(statementId)
      setReview(null)
      onResolved()
    } catch (error) {
      setErrorMessage(describe(error))
    } finally {
      setIsSubmitting(false)
    }
  }, [statementId, onResolved])

  return { review, choices, setChoice, submit, discard, status, errorMessage, isSubmitting }
}
