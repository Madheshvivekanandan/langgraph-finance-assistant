import { useCallback, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router'

const STORAGE_KEY = 'myfinance.chat.open'

/**
 * Per-route default, only applied where the rail can dock beside the
 * content (>=1120px). Below that width "open" means a full-screen overlay
 * sheet, and defaulting one open would bury the shell's own navigation
 * (including the hamburger that opens the nav drawer) under it on first
 * load — so every route defaults closed there until the person asks for it.
 */
function defaultOpenFor(pathname: string, canDock: boolean): boolean {
  if (!canDock) return false
  return pathname !== '/transactions'
}

/**
 * Open state for the chat rail (D3). Priority: `?chat=open` read once on
 * mount (the gate's deterministic handle), then `localStorage`, then a
 * per-route default. Toggling persists to `localStorage` only — the URL
 * param is never written back, so it stays a one-shot entry point.
 */
export function useChatRailState(canDock: boolean) {
  const location = useLocation()
  const [searchParams] = useSearchParams()

  const [open, setOpen] = useState<boolean>(() => {
    if (searchParams.get('chat') === 'open') return true
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null) return stored === 'true'
    return defaultOpenFor(location.pathname, canDock)
  })

  const setAndPersist = useCallback((next: boolean) => {
    setOpen(next)
    window.localStorage.setItem(STORAGE_KEY, String(next))
  }, [])

  const toggle = useCallback(() => setAndPersist(!open), [open, setAndPersist])
  const close = useCallback(() => setAndPersist(false), [setAndPersist])

  return { open, toggle, close, setOpen: setAndPersist }
}
