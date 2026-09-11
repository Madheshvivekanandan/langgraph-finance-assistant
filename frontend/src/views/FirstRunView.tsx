import { useNavigate } from 'react-router'
import { StatementUpload } from '../components/StatementUpload'
import { useFinanceDataContext } from '../hooks/useFinanceDataContext'

/**
 * Shown instead of the dashboard when there is no data yet
 * (`status === 'ready' && statements.length === 0`, D2). One heading naming
 * what will live here, one action, nothing else.
 */
export function FirstRunView() {
  const navigate = useNavigate()
  const { reload } = useFinanceDataContext()

  return (
    <div className="first-run">
      <h2>Where your money went, and what you can ask about it</h2>
      <p className="message">
        Upload a bank statement CSV to see spending broken down by month and category, and to ask
        the chat agent questions about it.
      </p>
      <StatementUpload
        onUploaded={() => {
          void reload()
          navigate('/statements')
        }}
      />
    </div>
  )
}
