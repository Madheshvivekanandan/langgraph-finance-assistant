import type { CategoryList } from '../interfaces/category'
import type { ProblemDetail } from '../interfaces/problem'
import type { Statement, StatementList } from '../interfaces/statement'
import type { CategorySummaryList, MonthSummaryList } from '../interfaces/summary'
import type { Transaction, TransactionPage } from '../interfaces/transaction'

const API_BASE = '/api/v1'
const REQUEST_TIMEOUT_MS = 30_000

/** An API error carrying the server's stable machine-readable code. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(problem: ProblemDetail) {
    super(problem.detail)
    this.name = 'ApiError'
    this.code = problem.code
    this.status = problem.status
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const problem = (await response.json()) as ProblemDetail
    if (problem.code) return new ApiError(problem)
  } catch {
    // Fall through to the generic shape below.
  }
  return new ApiError({
    type: 'about:blank',
    title: 'Request failed',
    status: response.status,
    detail: `The server responded with ${response.status}.`,
    code: 'UNEXPECTED_ERROR',
  })
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  })
  if (!response.ok) throw await toApiError(response)
  return (await response.json()) as T
}

export function uploadStatement(file: File): Promise<Statement> {
  const body = new FormData()
  body.append('file', file)
  return request<Statement>('/statements', { method: 'POST', body })
}

export function fetchStatements(): Promise<StatementList> {
  return request<StatementList>('/statements')
}

export interface TransactionFilters {
  month?: string | null
  category?: string | null
}

export function fetchTransactions(
  filters: TransactionFilters = {},
  pageToken?: string,
): Promise<TransactionPage> {
  const params = new URLSearchParams({ page_size: '50' })
  if (pageToken) params.set('page_token', pageToken)
  // The cursor carries a position only, so every page must resend the filters.
  if (filters.month) params.set('month', filters.month)
  if (filters.category) params.set('category', filters.category)
  return request<TransactionPage>(`/transactions?${params.toString()}`)
}

export function fetchMonthlySummary(): Promise<MonthSummaryList> {
  return request<MonthSummaryList>('/summary/months')
}

export function fetchCategorySummary(month?: string | null): Promise<CategorySummaryList> {
  const params = new URLSearchParams()
  if (month) params.set('month', month)
  const query = params.toString()
  return request<CategorySummaryList>(`/summary/categories${query ? `?${query}` : ''}`)
}

export function fetchCategories(): Promise<CategoryList> {
  return request<CategoryList>('/categories')
}

export function setTransactionCategory(
  transactionId: number,
  category: string,
): Promise<Transaction> {
  return request<Transaction>(`/transactions/${transactionId}/category`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
}
