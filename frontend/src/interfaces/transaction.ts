export type TransactionDirection = 'DEBIT' | 'CREDIT'

export type CategorizationSource = 'NONE' | 'RULE' | 'LLM' | 'USER'

export interface Transaction {
  id: number
  statement_id: number
  transaction_date: string
  description: string
  /** Decimal string, never a float — parse only for display. */
  amount: string
  direction: TransactionDirection
  category: string
  categorized_by: CategorizationSource
  /** Only present when a model made the guess. */
  confidence?: number
}

export interface TransactionPage {
  items: Transaction[]
  /** Absent on the last page. */
  next?: string
}
