import type { Category } from '../interfaces/category'
import type { Transaction } from '../interfaces/transaction'
import { formatAmountInr, formatIsoDate } from '../utils/formatters'

interface Props {
  transactions: Transaction[]
  categories: Category[]
  savingIds: ReadonlySet<number>
  hasMore: boolean
  isLoadingMore: boolean
  onLoadMore: () => void
  onCategoryChange: (transactionId: number, category: string) => void
}

/** Explains where a category came from, so a low-confidence guess is visible. */
function sourceHint(transaction: Transaction): string {
  switch (transaction.categorized_by) {
    case 'RULE':
      return 'Matched by a keyword rule'
    case 'LLM':
      return `Suggested by the model${
        transaction.confidence === undefined
          ? ''
          : ` (${Math.round(transaction.confidence * 100)}% confident)`
      }`
    case 'USER':
      return 'Set by you'
    default:
      return 'Not categorized yet'
  }
}

export function TransactionTable({
  transactions,
  categories,
  savingIds,
  hasMore,
  isLoadingMore,
  onLoadMore,
  onCategoryChange,
}: Props) {
  if (transactions.length === 0) {
    return (
      <div className="panel">
        <h2>Transactions</h2>
        <p className="message">
          Nothing here yet. Upload a statement and its transactions appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>Transactions</h2>
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
            {transactions.map((transaction) => (
              <tr key={transaction.id}>
                <td className="date-cell">{formatIsoDate(transaction.transaction_date)}</td>
                <td>{transaction.description}</td>
                <td>
                  <select
                    aria-label={`Category for ${transaction.description}`}
                    title={sourceHint(transaction)}
                    className={`category-select source-${transaction.categorized_by.toLowerCase()}`}
                    value={transaction.category}
                    disabled={savingIds.has(transaction.id)}
                    onChange={(event) =>
                      onCategoryChange(transaction.id, event.target.value)
                    }
                  >
                    {transaction.category === 'UNCATEGORIZED' && (
                      <option value="UNCATEGORIZED">— uncategorized —</option>
                    )}
                    {categories.map((category) => (
                      <option key={category.code} value={category.code}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td
                  className={`numeric ${
                    transaction.direction === 'DEBIT' ? 'amount-debit' : 'amount-credit'
                  }`}
                >
                  {/* Sign is carried by direction, not by the stored amount. */}
                  {transaction.direction === 'DEBIT' ? '−' : '+'}
                  {formatAmountInr(transaction.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasMore && (
        <button type="button" onClick={onLoadMore} disabled={isLoadingMore}>
          {isLoadingMore ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  )
}
