import { useEffect, useRef, type RefObject } from 'react'

interface Options {
  /** Whether the dialog should be rendered at all. */
  open: boolean
  /** Whether it should render as a modal overlay (`showModal()`) or a docked,
   *  non-modal element (`show()`). Ignored while `open` is false. */
  modal: boolean
  /** Called when the dialog closes itself (Esc, or a future form submit) so
   *  React state does not fall out of sync with the DOM. */
  onClose?: () => void
}

/**
 * Reconciles a `<dialog>` element's imperative open/modal state against React
 * props (D3). `showModal()`/`show()`/`close()` are the only way to move a
 * `<dialog>` between modal and non-modal — there is no declarative attribute
 * for it — and calling `showModal()` on an already-open dialog throws
 * `InvalidStateError`, so every transition closes first.
 */
export function useDockableDialog(
  ref: RefObject<HTMLDialogElement | null>,
  { open, modal, onClose }: Options,
): void {
  // There is no reliable "am I currently modal" read except `matches(':modal')`,
  // which is also fine, but tracking it ourselves avoids a DOM read on every render.
  const modeRef = useRef<'closed' | 'modal' | 'docked'>('closed')

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return

    if (!open) {
      if (modeRef.current !== 'closed') {
        dialog.close()
        modeRef.current = 'closed'
      }
      return
    }

    const wantMode = modal ? 'modal' : 'docked'
    if (modeRef.current !== wantMode) {
      if (modeRef.current !== 'closed') dialog.close()
      if (wantMode === 'modal') {
        dialog.showModal()
      } else {
        dialog.show()
      }
      modeRef.current = wantMode
    }
  }, [ref, open, modal])

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    const handleClose = () => {
      modeRef.current = 'closed'
      onClose?.()
    }
    dialog.addEventListener('close', handleClose)
    return () => dialog.removeEventListener('close', handleClose)
  }, [ref, onClose])
}
