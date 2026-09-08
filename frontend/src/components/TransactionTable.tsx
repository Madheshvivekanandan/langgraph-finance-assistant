import type { Transaction } from '../interfaces/transaction'
import { formatAmountInr, formatIsoDate } from '../utils/formatters'

interface Props {
  transactions: Transaction[]
  hasMore: boolean
  isLoadingMore: boolean
  onLoadMore: () => void
}

export function TransactionTable({
  transactions,
  hasMore,
  isLoadingMore,
  onLoadMore,
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
      <table>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Description</th>
            <th scope="col" className="numeric">
              Amount
            </th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((transaction) => (
            <tr key={transaction.id}>
              <td>{formatIsoDate(transaction.transaction_date)}</td>
              <td>{transaction.description}</td>
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
      {hasMore && (
        <button type="button" onClick={onLoadMore} disabled={isLoadingMore}>
          {isLoadingMore ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  )
}
