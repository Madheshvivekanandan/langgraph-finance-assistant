const INR_FORMATTER = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
})

const DATE_FORMATTER = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

/**
 * Format a decimal-string amount for display.
 * The string stays authoritative; Number() is used only to render it.
 */
export function formatAmountInr(amount: string): string {
  return INR_FORMATTER.format(Number(amount))
}

/** Format an ISO date (YYYY-MM-DD) for display, without timezone shifting. */
export function formatIsoDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  return DATE_FORMATTER.format(new Date(year, month - 1, day))
}
