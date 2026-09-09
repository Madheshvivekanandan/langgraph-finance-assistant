export interface MonthSummary {
  /** "YYYY-MM" */
  month: string
  /** Decimal strings — parse only for display or chart geometry. */
  income: string
  expense: string
  net: string
  transaction_count: number
}

export interface MonthSummaryList {
  items: MonthSummary[]
}

export interface CategorySummary {
  category: string
  label: string
  amount: string
  transaction_count: number
}

export interface CategorySummaryList {
  month: string | null
  total: string
  items: CategorySummary[]
}
