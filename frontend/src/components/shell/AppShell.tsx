import { useEffect, useMemo, useState } from 'react'
import { Outlet } from 'react-router'
import { FinanceDataContext, type FinanceDataContextValue } from '../../context/FinanceDataContext'
import { useChatRailState } from '../../hooks/useChatRailState'
import { useFinanceData } from '../../hooks/useFinanceData'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { ErrorBoundary } from '../ErrorBoundary'
import { ChatRail } from './ChatRail'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

const DESKTOP_NAV_QUERY = '(min-width: 768px)'
const DOCKED_CHAT_QUERY = '(min-width: 1120px)'

/** Fires the toggle unless the event target is a form control that owns the keystroke. */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    target.isContentEditable
  )
}

/**
 * The persistent app shell: fetches finance data once, publishes it via
 * context, and renders the sidebar / top bar / routed outlet / chat rail
 * that every view shares (D2).
 */
export function AppShell() {
  const financeData = useFinanceData()
  const { statements, status, errorMessage } = financeData

  // .filter(), not .find(): two statements paused at once must both get a
  // panel, or the second one is silently unreachable.
  const awaitingReview = statements.filter((statement) => statement.status === 'AWAITING_REVIEW')

  const contextValue = useMemo<FinanceDataContextValue>(
    () => ({ ...financeData, awaitingReview }),
    [financeData, awaitingReview],
  )

  const [navOpen, setNavOpen] = useState(false)
  const isDesktopNav = useMediaQuery(DESKTOP_NAV_QUERY)
  const isDockedChat = useMediaQuery(DOCKED_CHAT_QUERY)
  const chatRail = useChatRailState(isDockedChat)

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'j'
      if (!isShortcut || isTypingTarget(event.target)) return
      event.preventDefault()
      chatRail.toggle()
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [chatRail])

  return (
    <FinanceDataContext.Provider value={contextValue}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app">
        <Sidebar
          open={isDesktopNav || navOpen}
          modal={!isDesktopNav}
          onClose={() => setNavOpen(false)}
          awaitingReviewCount={awaitingReview.length}
        />

        <div className="shell-main">
          <TopBar
            onOpenNav={() => setNavOpen(true)}
            chatOpen={chatRail.open}
            onToggleChat={chatRail.toggle}
          />

          <main id="main" className="shell-content">
            {status === 'loading' && <p className="message">Loading…</p>}

            {status === 'error' && (
              <p className="message message-error" role="alert">
                {errorMessage}
              </p>
            )}

            {status === 'ready' && (
              <ErrorBoundary>
                <Outlet />
              </ErrorBoundary>
            )}
          </main>
        </div>

        <ChatRail open={chatRail.open} docked={isDockedChat} onClose={chatRail.close} />
      </div>
    </FinanceDataContext.Provider>
  )
}
