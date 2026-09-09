import type { Category } from '../interfaces/category'
import type { CategorySummaryList, MonthSummary } from '../interfaces/summary'
import { formatAmountInr, formatMonthLabel } from '../utils/formatters'
import { CategoryBarChart } from './CategoryBarChart'
import { StatTile } from './StatTile'
import { TrendLineChart } from './TrendLineChart'

interface Props {
  months: MonthSummary[]
  categorySummary: CategorySummaryList | null
  categories: Category[]
  selectedMonth: string | null
  onMonthChange: (month: string | null) => void
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
}

function labelFor(categories: Category[], code: string): string {
  return categories.find((item) => item.code === code)?.label ?? code
}

export function Dashboard({
  months,
  categorySummary,
  categories,
  selectedMonth,
  onMonthChange,
  selectedCategory,
  onCategoryChange,
}: Props) {
  if (months.length === 0) {
    return (
      <div className="panel">
        <h2>Dashboard</h2>
        <p className="message">Upload a statement and your spending appears here.</p>
      </div>
    )
  }

  // Totals for the selected month, or every month summed when showing all time.
  const scope = selectedMonth ? months.filter((item) => item.month === selectedMonth) : months
  const income = scope.reduce((sum, item) => sum + Number(item.income), 0)
  const expense = scope.reduce((sum, item) => sum + Number(item.expense), 0)
  const net = income - expense

  return (
    <>
      <div className="panel">
        {/* Filters sit in one row above the charts they control. */}
        <div className="filter-row">
          <label htmlFor="month-filter">Period</label>
          <select
            id="month-filter"
            value={selectedMonth ?? ''}
            onChange={(event) => onMonthChange(event.target.value || null)}
          >
            <option value="">All time</option>
            {months.map((month) => (
              <option key={month.month} value={month.month}>
                {formatMonthLabel(month.month)}
              </option>
            ))}
          </select>

          {selectedCategory && (
            <button
              type="button"
              className="chip-clear"
              onClick={() => onCategoryChange(null)}
            >
              {labelFor(categories, selectedCategory)} ✕
            </button>
          )}
        </div>

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
      </div>

      <div className="panel">
        <h2>Income and expense by month</h2>
        {/* Oldest first: the x-axis reads left to right. */}
        <TrendLineChart months={[...months].reverse()} />
      </div>

      <div className="panel">
        <h2>
          Where the money went
          {selectedMonth ? ` · ${formatMonthLabel(selectedMonth)}` : ' · all time'}
        </h2>
        <p className="message">Select a bar to filter the transactions below.</p>
        <CategoryBarChart
          items={categorySummary?.items ?? []}
          total={categorySummary?.total ?? '0'}
          selectedCategory={selectedCategory}
          onSelect={onCategoryChange}
        />
      </div>
    </>
  )
}
