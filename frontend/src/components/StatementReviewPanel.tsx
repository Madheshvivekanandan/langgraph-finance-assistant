import type { Category } from '../interfaces/category'
import { useStatementReview } from '../hooks/useStatementReview'
import { formatAmountInr, formatIsoDate } from '../utils/formatters'

interface Props {
  statementId: number
  filename: string
  categories: Category[]
  onResolved: () => void
}

function confirmDiscard(): boolean {
  return window.confirm(
    'Discard this statement? This permanently deletes it and cannot be undone.',
  )
}

/** Renders only for a statement paused AWAITING_REVIEW; approving resumes its run. */
export function StatementReviewPanel({ statementId, filename, categories, onResolved }: Props) {
  const { review, choices, setChoice, submit, discard, status, errorMessage, isSubmitting } =
    useStatementReview(statementId, onResolved)

  if (status === 'loading') {
    return (
      <div className="panel">
        <h2>Review needed</h2>
        <p className="message">Loading the rows to confirm…</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="panel">
        <h2>Review needed</h2>
        <p className="message message-error" role="alert">
          {errorMessage}
        </p>
        <button
          type="button"
          onClick={() => confirmDiscard() && void discard()}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Discarding…' : 'Discard'}
        </button>
      </div>
    )
  }

  if (!review) return null

  return (
    <div className="panel panel-review">
      <h2>
        Review needed — {filename}{' '}
        <span className="badge badge-awaiting_review">{review.items.length} to review</span>
      </h2>
      <p className="message">
        The model was unsure about {review.items.length} row
        {review.items.length === 1 ? '' : 's'}. Confirm or correct each, then approve to finish
        storing this statement.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Description</th>
              <th scope="col">Category</th>
              <th scope="col" className="numeric">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {review.items.map((item) => (
              <tr key={item.index}>
                <td className="date-cell">{formatIsoDate(item.transaction_date)}</td>
                <td>{item.description}</td>
                <td>
                  <select
                    aria-label={`Category for ${item.description}`}
                    title={`Suggested by the model (${Math.round(
                      Number(item.confidence) * 100,
                    )}% confident)`}
                    className="category-select source-llm"
                    value={choices[item.index] ?? item.suggested_category}
                    disabled={isSubmitting}
                    onChange={(event) => setChoice(item.index, event.target.value)}
                  >
                    {categories.map((category) => (
                      <option key={category.code} value={category.code}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td
                  className={`numeric ${
                    item.direction === 'DEBIT' ? 'amount-debit' : 'amount-credit'
                  }`}
                >
                  {item.direction === 'DEBIT' ? '−' : '+'}
                  {formatAmountInr(item.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel-review-actions">
        <button type="button" onClick={() => void submit()} disabled={isSubmitting}>
          {isSubmitting ? 'Submitting…' : 'Approve'}
        </button>
        <button
          type="button"
          onClick={() => confirmDiscard() && void discard()}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Discarding…' : 'Discard'}
        </button>
      </div>
    </div>
  )
}
