import { useState } from 'react'
import type { MonthSummary } from '../interfaces/summary'
import { formatAmountInr, formatMonthLabel } from '../utils/formatters'

interface Props {
  /** Oldest first — the order the x-axis reads in. */
  months: MonthSummary[]
}

const VIEW_WIDTH = 720
const VIEW_HEIGHT = 260
const PADDING = { top: 16, right: 16, bottom: 32, left: 64 }
const PLOT_WIDTH = VIEW_WIDTH - PADDING.left - PADDING.right
const PLOT_HEIGHT = VIEW_HEIGHT - PADDING.top - PADDING.bottom
const GRID_LINES = 4

/** Compact axis labels: 85000 reads as ₹85k. */
function compactInr(value: number): string {
  if (value >= 10_000_000) return `₹${(value / 10_000_000).toFixed(1)}Cr`
  if (value >= 100_000) return `₹${(value / 100_000).toFixed(1)}L`
  if (value >= 1_000) return `₹${Math.round(value / 1_000)}k`
  return `₹${Math.round(value)}`
}

/**
 * Income and expense over time.
 *
 * Two series on ONE shared axis — both are rupees, so a second y-scale would let
 * the two lines cross wherever the scales happened to put them and imply a
 * relationship that is not in the data.
 */
export function TrendLineChart({ months }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)

  if (months.length === 0) {
    return <p className="message">No months to plot yet.</p>
  }

  const peak = Math.max(
    ...months.map((month) => Math.max(Number(month.income), Number(month.expense))),
    1,
  )
  // Round the axis top up to something readable rather than the raw maximum.
  const magnitude = 10 ** Math.floor(Math.log10(peak))
  const axisMax = Math.ceil(peak / magnitude) * magnitude

  const xAt = (index: number) =>
    months.length === 1
      ? PADDING.left + PLOT_WIDTH / 2
      : PADDING.left + (index / (months.length - 1)) * PLOT_WIDTH
  const yAt = (value: number) =>
    PADDING.top + PLOT_HEIGHT * (1 - value / axisMax)

  const path = (pick: (month: MonthSummary) => string) =>
    months
      .map((month, index) => `${index === 0 ? 'M' : 'L'} ${xAt(index)} ${yAt(Number(pick(month)))}`)
      .join(' ')

  function handleMove(event: React.MouseEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const ratio = (event.clientX - bounds.left) / bounds.width
    const svgX = ratio * VIEW_WIDTH
    let nearest = 0
    let best = Infinity
    months.forEach((_, index) => {
      const distance = Math.abs(xAt(index) - svgX)
      if (distance < best) {
        best = distance
        nearest = index
      }
    })
    setHovered(nearest)
  }

  const active = hovered === null ? null : months[hovered]

  return (
    <div className="chart-frame">
      <ul className="legend">
        <li>
          <span className="legend-swatch swatch-income" /> Income
        </li>
        <li>
          <span className="legend-swatch swatch-expense" /> Expense
        </li>
      </ul>

      <svg
        className="trend-chart"
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        role="img"
        aria-label="Income and expense by month"
        onMouseMove={handleMove}
        onMouseLeave={() => setHovered(null)}
      >
        {Array.from({ length: GRID_LINES + 1 }, (_, step) => {
          const value = (axisMax / GRID_LINES) * step
          const y = yAt(value)
          return (
            <g key={step}>
              <line
                x1={PADDING.left}
                x2={VIEW_WIDTH - PADDING.right}
                y1={y}
                y2={y}
                className="grid-line"
              />
              <text x={PADDING.left - 8} y={y + 4} className="axis-label" textAnchor="end">
                {compactInr(value)}
              </text>
            </g>
          )
        })}

        {months.map((month, index) => {
          // Past 6 months the labels start to crowd; keep every other one
          // (always keeping the last) rather than letting them overlap.
          const isSkippable =
            months.length > 6 && index !== months.length - 1 && index % 2 !== 0
          if (isSkippable) return null
          return (
            <text
              key={month.month}
              x={xAt(index)}
              y={VIEW_HEIGHT - 10}
              className="axis-label"
              // The end labels anchor inward, or half of each sits outside the
              // viewBox and gets clipped.
              textAnchor={
                months.length === 1
                  ? 'middle'
                  : index === 0
                    ? 'start'
                    : index === months.length - 1
                      ? 'end'
                      : 'middle'
              }
            >
              {formatMonthLabel(month.month)}
            </text>
          )
        })}

        {hovered !== null && (
          <line
            x1={xAt(hovered)}
            x2={xAt(hovered)}
            y1={PADDING.top}
            y2={PADDING.top + PLOT_HEIGHT}
            className="crosshair"
          />
        )}

        <path d={path((month) => month.income)} className="series-line line-income" />
        <path d={path((month) => month.expense)} className="series-line line-expense" />

        {months.map((month, index) => (
          <g key={month.month}>
            <circle
              cx={xAt(index)}
              cy={yAt(Number(month.income))}
              r={hovered === index ? 6 : 4}
              className="series-dot dot-income"
            />
            <circle
              cx={xAt(index)}
              cy={yAt(Number(month.expense))}
              r={hovered === index ? 6 : 4}
              className="series-dot dot-expense"
            />
          </g>
        ))}
      </svg>

      {active && (
        <div
          className="chart-tooltip trend-tooltip"
          style={{ left: `${(xAt(hovered ?? 0) / VIEW_WIDTH) * 100}%` }}
          role="status"
        >
          <strong>{formatMonthLabel(active.month)}</strong>
          <span>Income {formatAmountInr(active.income)}</span>
          <span>Expense {formatAmountInr(active.expense)}</span>
          <span>Net {formatAmountInr(active.net)}</span>
        </div>
      )}
    </div>
  )
}
