interface Props {
  label: string
  value: string
  /** Secondary encoding for net, so the meaning is never colour alone. */
  sign?: 'positive' | 'negative'
  detail?: string
}

/**
 * A single headline number. A stat tile, not a one-bar chart: a lone value has
 * nothing to compare against, so a plot would add ink without adding meaning.
 */
export function StatTile({ label, value, sign, detail }: Props) {
  return (
    <div className="stat-tile">
      <span className="stat-label">{label}</span>
      <span className={`stat-value ${sign ? `stat-${sign}` : ''}`}>
        {sign === 'positive' ? '+' : sign === 'negative' ? '−' : ''}
        {value}
      </span>
      {detail && <span className="stat-detail">{detail}</span>}
    </div>
  )
}
