import { useState } from 'react'
import type { CategorySummary } from '../interfaces/summary'
import { formatAmountInr } from '../utils/formatters'

interface Props {
  items: CategorySummary[]
  total: string
  onSelect: (category: string | null) => void
  selectedCategory: string | null
}

/**
 * Spending by category, largest first.
 *
 * A bar chart, not a donut: the reader's job is comparing magnitudes, and bar
 * length is far easier to compare than arc angle. One hue throughout — length
 * already carries the magnitude, so varying colour would encode nothing.
 */
export function CategoryBarChart({ items, total, onSelect, selectedCategory }: Props) {
  const [hovered, setHovered] = useState<string | null>(null)

  if (items.length === 0) {
    return <p className="message">No spending in this period.</p>
  }

  const totalAmount = Number(total)
  const largest = Math.max(...items.map((item) => Number(item.amount)))

  return (
    <ul className="bar-chart">
      {items.map((item) => {
        const amount = Number(item.amount)
        const share = totalAmount > 0 ? (amount / totalAmount) * 100 : 0
        const isSelected = selectedCategory === item.category
        return (
          <li key={item.category}>
            <button
              type="button"
              className={`bar-row ${isSelected ? 'bar-row-selected' : ''}`}
              onClick={() => onSelect(isSelected ? null : item.category)}
              onMouseEnter={() => setHovered(item.category)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(item.category)}
              onBlur={() => setHovered(null)}
              aria-pressed={isSelected}
            >
              <span className="bar-label">
                <span className="bar-dot" data-category={item.category} aria-hidden="true" />
                {item.label}
              </span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${largest > 0 ? (amount / largest) * 100 : 0}%` }}
                />
              </span>
              <span className="bar-value">{formatAmountInr(item.amount)}</span>
            </button>
            {hovered === item.category && (
              <div className="chart-tooltip bar-tooltip" role="status">
                {item.label}: {formatAmountInr(item.amount)} · {share.toFixed(1)}% ·{' '}
                {item.transaction_count} txn{item.transaction_count === 1 ? '' : 's'}
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
