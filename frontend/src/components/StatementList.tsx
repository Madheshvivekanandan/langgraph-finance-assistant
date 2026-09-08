import type { Statement } from '../interfaces/statement'
import { formatIsoDate } from '../utils/formatters'

interface Props {
  statements: Statement[]
}

function periodLabel(statement: Statement): string {
  if (!statement.period_start || !statement.period_end) return '—'
  return `${formatIsoDate(statement.period_start)} – ${formatIsoDate(statement.period_end)}`
}

export function StatementList({ statements }: Props) {
  if (statements.length === 0) {
    return (
      <div className="panel">
        <h2>Statements</h2>
        <p className="message">No statements yet. Upload one to get started.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>Statements</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">File</th>
            <th scope="col">Status</th>
            <th scope="col">Transactions</th>
            <th scope="col">Period</th>
          </tr>
        </thead>
        <tbody>
          {statements.map((statement) => (
            <tr key={statement.id}>
              <td>{statement.filename}</td>
              <td>
                <span className={`badge badge-${statement.status.toLowerCase()}`}>
                  {statement.status}
                </span>
                {statement.error_message && (
                  <div className="message message-error">{statement.error_message}</div>
                )}
              </td>
              <td className="numeric">{statement.transaction_count}</td>
              <td>{periodLabel(statement)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
