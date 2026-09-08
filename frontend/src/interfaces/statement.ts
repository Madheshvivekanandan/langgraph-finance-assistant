export type StatementStatus = 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface Statement {
  id: number
  filename: string
  status: StatementStatus
  transaction_count: number
  period_start: string | null
  period_end: string | null
  error_message: string | null
  created_at: string
}

export interface StatementList {
  items: Statement[]
}
