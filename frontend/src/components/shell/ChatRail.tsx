import { useEffect, useRef } from 'react'
import { ChatPanel } from '../ChatPanel'
import { ErrorBoundary } from '../ErrorBoundary'
import { useDockableDialog } from '../../hooks/useDockableDialog'

interface Props {
  open: boolean
  /** Docked (grid, non-modal `show()`) vs overlay (`showModal()`) — follows width, not choice. */
  docked: boolean
  onClose: () => void
}

/**
 * The single always-mounted chat surface (D3). Never conditionally rendered:
 * `useChat`'s thread lives inside `ChatPanel`, and remounting it on every
 * open/close or docked/overlay transition would wipe the conversation.
 */
export function ChatRail({ open, docked, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  useDockableDialog(dialogRef, { open, modal: !docked, onClose })

  useEffect(() => {
    if (open) {
      previouslyFocused.current = document.activeElement as HTMLElement | null
      const frame = requestAnimationFrame(() => {
        dialogRef.current
          ?.querySelector<HTMLInputElement>('.chat-composer-row input')
          ?.focus()
      })
      return () => cancelAnimationFrame(frame)
    }
    previouslyFocused.current?.focus()
    return undefined
  }, [open])

  return (
    <dialog id="chat-rail-dialog" ref={dialogRef} className="chat-rail" aria-label="Chat">
      <ErrorBoundary>
        <ChatPanel onClose={onClose} />
      </ErrorBoundary>
    </dialog>
  )
}
