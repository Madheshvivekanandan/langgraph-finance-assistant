import { Link, useNavigate } from 'react-router'
import { CategoryBarChart } from '../components/CategoryBarChart'
import { EmptyState } from '../components/EmptyState'
import { RecentTransactions } from '../components/RecentTransactions'
import { StatTile } from '../components/StatTile'
import { TrendLineChart } from '../components/TrendLineChart'
import { useFinanceDataContext } from '../hooks/useFinanceDataContext'
import { formatAmountInr } from '../utils/formatters'
import { FirstRunView } from './FirstRunView'

function labelFor(categories: { code: string; label: string }[], code: string): string {
  return categories.find((item) => item.code === code)?.label ?? code
}

/**
 * The landing view: a review banner when statements are paused, a KPI strip,
 * a full-width trend chart, then category breakdown + recent transactions
 * side by side (D2). Delegates to `FirstRunView` with no data at all.
 */
export function OverviewView() {
  const navigate = useNavigate()
  const {
    statements,
    months,
    categorySummary,
    categories,
    selectedMonth,
    selectedCategory,
    setSelectedCategory,
    transactions,
    awaitingReview,
  } = useFinanceDataContext()

  if (statements.length === 0) {
    return (
      <div data-view="overview">
        <FirstRunView />
      </div>
    )
  }

  // Totals for the selected month, or every month summed when showing all time.
  // Lifted verbatim from the old Dashboard.tsx (D6).
  const scope = selectedMonth ? months.filter((item) => item.month === selectedMonth) : months
  const income = scope.reduce((sum, item) => sum + Number(item.income), 0)
  const expense = scope.reduce((sum, item) => sum + Number(item.expense), 0)
  const net = income - expense

  return (
    <div data-view="overview">
      {awaitingReview.length > 0 && (
        <div className="panel panel-review overview-banner">
          <p className="message">
            {awaitingReview.length} statement{awaitingReview.length === 1 ? '' : 's'} paused,
            waiting for you to confirm a few categories.
          </p>
          <Link to="/review">Review now →</Link>
        </div>
      )}

      {months.length === 0 ? (
        <EmptyState title="No spending yet">
          Upload a statement to see it summarized here.
        </EmptyState>
      ) : (
        <>
          <div className="kpi-row">
            <StatTile label="Income" value={formatAmountInr(String(income))} />
            <StatTile label="Expense" value={formatAmountInr(String(expense))} />
            <StatTile
              label="Net"
              value={formatAmountInr(String(Math.abs(net)))}
              sign={net >= 0 ? 'positive' : 'negative'}
              detail={net >= 0 ? 'saved' : 'overspent'}
            />
          </div>

          <div className="panel overview-trend">
            <h2>Income and expense by month</h2>
            {/* Oldest first: the x-axis reads left to right. */}
            <TrendLineChart months={[...months].reverse()} />
          </div>

          <div className="overview-grid">
            <div className="panel overview-categories">
              <h2>
                Where the money went
                {selectedCategory && (
                  <>
                    {' · '}
                    <button
                      type="button"
                      className="chip-clear"
                      onClick={() => setSelectedCategory(null)}
                    >
                      {labelFor(categories, selectedCategory)} ✕
                    </button>
                  </>
                )}
              </h2>
              <p className="message">Select a bar to filter transactions.</p>
              <CategoryBarChart
                items={categorySummary?.items ?? []}
                total={categorySummary?.total ?? '0'}
                selectedCategory={selectedCategory}
                onSelect={(category) => {
                  setSelectedCategory(category)
                  if (category) navigate('/transactions')
                }}
              />
            </div>

            <div className="panel overview-recent">
              <h2>Recent transactions</h2>
              <RecentTransactions transactions={transactions} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
