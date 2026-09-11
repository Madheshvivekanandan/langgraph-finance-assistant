import { Link } from 'react-router'
import type { Transaction } from '../interfaces/transaction'
import { formatAmountInr, formatIsoDate } from '../utils/formatters'

const PREVIEW_ROWS = 6

interface Props {
  transactions: Transaction[]
}

/** A read-only, 6-row preview of the latest transactions, linking to the full table. */
export function RecentTransactions({ transactions }: Props) {
  if (transactions.length === 0) {
    return <p className="message">No transactions yet.</p>
  }

  const preview = transactions.slice(0, PREVIEW_ROWS)

  return (
    <>
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
            {preview.map((transaction) => (
              <tr key={transaction.id}>
                <td className="date-cell">{formatIsoDate(transaction.transaction_date)}</td>
                <td>{transaction.description}</td>
                <td data-category={transaction.category}>
                  <span className="category-dot" aria-hidden="true" />
                  {transaction.category}
                </td>
                <td
                  className={`numeric ${
                    transaction.direction === 'DEBIT' ? 'amount-debit' : 'amount-credit'
                  }`}
                >
                  {transaction.direction === 'DEBIT' ? '−' : '+'}
                  {formatAmountInr(transaction.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Link className="recent-transactions-link" to="/transactions">
        View all →
      </Link>
    </>
  )
}
