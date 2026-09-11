import { createContext } from 'react'
import type { Statement } from '../interfaces/statement'
import type { useFinanceData } from '../hooks/useFinanceData'

/** Everything `useFinanceData()` returns, plus the shell's derived `awaitingReview` list. */
export type FinanceDataContextValue = ReturnType<typeof useFinanceData> & {
  /** Statements paused for human review — computed once in AppShell, shared by the
   *  sidebar badge and ReviewView so there is one source, not a second fetch. */
  awaitingReview: Statement[]
}

export const FinanceDataContext = createContext<FinanceDataContextValue | null>(null)
