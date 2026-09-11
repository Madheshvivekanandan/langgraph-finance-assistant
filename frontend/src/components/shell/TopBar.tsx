import { useLocation } from 'react-router'
import { useFinanceDataContext } from '../../hooks/useFinanceDataContext'
import { formatMonthLabel } from '../../utils/formatters'

const VIEW_TITLES: Record<string, string> = {
  '/': 'Overview',
  '/transactions': 'Transactions',
  '/statements': 'Statements',
  '/review': 'Review',
  '/pipeline': 'Pipeline',
}

const ROUTES_WITH_PERIOD_FILTER = new Set(['/', '/transactions'])

interface Props {
  onOpenNav: () => void
  chatOpen: boolean
  onToggleChat: () => void
}

/** Sticky top bar: nav toggle (mobile only), the one `<h1>` per view, an
 *  optional period filter, and the chat toggle (D2). */
export function TopBar({ onOpenNav, chatOpen, onToggleChat }: Props) {
  const location = useLocation()
  const { months, selectedMonth, setSelectedMonth } = useFinanceDataContext()
  const title = VIEW_TITLES[location.pathname] ?? 'My Finance'
  const showPeriodFilter = ROUTES_WITH_PERIOD_FILTER.has(location.pathname) && months.length > 0

  return (
    <header className="topbar">
      <button
        type="button"
        className="nav-toggle"
        data-nav-toggle
        aria-label="Open navigation"
        onClick={onOpenNav}
      >
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path
            d="M4 6h16M4 12h16M4 18h16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {/* tabIndex=-1: focusable by script (route-change focus management) but not by Tab. */}
      <h1 className="view-title" tabIndex={-1}>
        {title}
      </h1>

      {showPeriodFilter && (
        <div className="topbar-filter">
          <label htmlFor="period-filter">Period</label>
          <select
            id="period-filter"
            aria-label="Period"
            value={selectedMonth ?? ''}
            onChange={(event) => setSelectedMonth(event.target.value || null)}
          >
            <option value="">All time</option>
            {months.map((month) => (
              <option key={month.month} value={month.month}>
                {formatMonthLabel(month.month)}
              </option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        className="chat-toggle"
        data-chat-toggle
        aria-expanded={chatOpen}
        aria-controls="chat-rail-dialog"
        title="Chat (Cmd/Ctrl+J)"
        onClick={onToggleChat}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            d="M4 5h16v11H8l-4 4z"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </svg>
        <span className="chat-toggle-label">Chat</span>
      </button>
    </header>
  )
}
