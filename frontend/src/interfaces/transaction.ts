export type TransactionDirection = 'DEBIT' | 'CREDIT'

export interface Transaction {
  id: number
  statement_id: number
  transaction_date: string
  description: string
  /** Decimal string, never a float — parse only for display. */
  amount: string
  direction: TransactionDirection
}

export interface TransactionPage {
  items: Transaction[]
  /** Absent on the last page. */
  next?: string
}
