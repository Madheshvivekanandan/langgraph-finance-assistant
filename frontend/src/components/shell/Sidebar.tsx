import { useRef } from 'react'
import { NavLink, useNavigate } from 'react-router'
import { useDockableDialog } from '../../hooks/useDockableDialog'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  end?: boolean
}

/** Minimal inline glyphs — no icon library dependency (D7 scope guard). */
const ICONS = {
  overview: (
    <path d="M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 9h6V4h-6z" />
  ),
  transactions: <path d="M4 6h16M4 12h16M4 18h10" strokeLinecap="round" fill="none" stroke="currentColor" strokeWidth="2" />,
  statements: <path d="M6 3h9l5 5v13H6zM14 3v5h5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  review: <path d="M20 6 9 17l-5-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />,
  pipeline: <path d="M4 6h4v4H4zM16 14h4v4h-4zM8 8h5a3 3 0 0 1 3 3v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />,
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Overview', icon: ICONS.overview, end: true },
  { to: '/transactions', label: 'Transactions', icon: ICONS.transactions },
  { to: '/statements', label: 'Statements', icon: ICONS.statements },
  { to: '/review', label: 'Review', icon: ICONS.review },
  { to: '/pipeline', label: 'Pipeline', icon: ICONS.pipeline },
]

interface Props {
  open: boolean
  modal: boolean
  onClose: () => void
  awaitingReviewCount: number
}

export function Sidebar({ open, modal, onClose, awaitingReviewCount }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const navigate = useNavigate()
  useDockableDialog(dialogRef, { open, modal, onClose })

  return (
    <dialog ref={dialogRef} className="sidebar" aria-label="Primary navigation">
      <div className="sidebar-inner">
        <div className="sidebar-header">
          <span className="wordmark">My Finance</span>
        </div>

        <nav aria-label="Primary">
          <ul className="nav-list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `nav-item ${isActive ? 'nav-item-active' : ''}`}
                  onClick={modal ? onClose : undefined}
                >
                  <svg
                    className="nav-item-icon"
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    aria-hidden="true"
                  >
                    {item.icon}
                  </svg>
                  <span className="nav-item-label">{item.label}</span>
                  {item.to === '/review' && awaitingReviewCount > 0 && (
                    <span className="badge-count">{awaitingReviewCount}</span>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <button
          type="button"
          className="sidebar-upload-button"
          onClick={() => {
            navigate('/statements')
            if (modal) onClose()
          }}
        >
          Upload statement
        </button>
      </div>
    </dialog>
  )
}
