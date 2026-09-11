import { useContext } from 'react'
import { FinanceDataContext, type FinanceDataContextValue } from '../context/FinanceDataContext'

/** Consumes the finance data published by `AppShell`. Throws outside the provider so a
 *  view rendered outside the shell fails loudly instead of silently reading `null`. */
export function useFinanceDataContext(): FinanceDataContextValue {
  const value = useContext(FinanceDataContext)
  if (!value) {
    throw new Error('useFinanceDataContext must be used within AppShell')
  }
  return value
}
