import { EmptyState } from '../components/EmptyState'
import { StatementReviewPanel } from '../components/StatementReviewPanel'
import { useFinanceDataContext } from '../hooks/useFinanceDataContext'

export function ReviewView() {
  const { awaitingReview, categories, reload } = useFinanceDataContext()

  return (
    <div data-view="review">
      {awaitingReview.length === 0 ? (
        <EmptyState title="Nothing to review">
          Statements the model was unsure about will show up here for you to confirm.
        </EmptyState>
      ) : (
        awaitingReview.map((statement) => (
          <StatementReviewPanel
            key={statement.id}
            statementId={statement.id}
            filename={statement.filename}
            categories={categories}
            onResolved={() => void reload()}
          />
        ))
      )}
    </div>
  )
}
