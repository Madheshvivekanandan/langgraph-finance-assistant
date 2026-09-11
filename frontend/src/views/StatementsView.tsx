import { StatementList } from '../components/StatementList'
import { StatementUpload } from '../components/StatementUpload'
import { useFinanceDataContext } from '../hooks/useFinanceDataContext'

export function StatementsView() {
  const { statements, reload } = useFinanceDataContext()

  return (
    <div data-view="statements">
      <StatementUpload onUploaded={() => void reload()} />
      <StatementList statements={statements} />
    </div>
  )
}
