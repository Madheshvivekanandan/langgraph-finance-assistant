import type { TransactionDirection } from './transaction'

/** One low-confidence row a person must confirm or correct. */
export interface StatementReviewItem {
  index: number
  transaction_date: string
  description: string
  /** Decimal string, never a float — parse only for display. */
  amount: string
  direction: TransactionDirection
  suggested_category: string
  /** Decimal string, never a float — parse only for display. */
  confidence: string
}

/** Everything a paused statement's run is asking a person to confirm. */
export interface StatementReview {
  statement_id: number
  filename: string
  threshold: string
  items: StatementReviewItem[]
}

/** A person's corrected category for one pending row. */
export interface StatementReviewDecision {
  index: number
  category: string
}
