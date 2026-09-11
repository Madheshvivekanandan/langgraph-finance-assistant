import { useEffect, useId, useRef, useState } from 'react'
import { useChat } from '../hooks/useChat'
import { ChatMessage } from './ChatMessage'

interface Props {
  /** Closes the surface the panel lives in (the rail's `<dialog>`), so the
   *  overlay sheet has a visible dismiss control and not only Esc / the
   *  top-bar toggle it covers. */
  onClose: () => void
}

/**
 * Ask questions about the stored transactions, answered by the chat agent and
 * streamed token by token. A status gate gets out of the way before anyone
 * types, rather than failing after the fact.
 *
 * Laid out as a full-height column (M5): header, then the thread as the only
 * flexing, scrolling child, then the composer. That is what pins the composer
 * to the bottom of the rail instead of leaving it stranded under the header
 * with empty rail beneath it.
 */
export function ChatPanel({ onClose }: Props) {
  const { messages, isStreaming, error, available, send, newChat } = useChat()
  const [draft, setDraft] = useState('')
  const inputId = useId()
  const listRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    const list = listRef.current
    if (list) list.scrollTop = list.scrollHeight
  }, [messages])

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!draft.trim() || isStreaming) return
    const text = draft
    setDraft('')
    void send(text)
  }

  const closeButton = (
    <button type="button" className="chat-close-button" aria-label="Close chat" onClick={onClose}>
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          d="M6 6l12 12M18 6L6 18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </button>
  )

  if (available === false) {
    return (
      <section className="chat-panel">
        <div className="chat-header">
          <h2>Ask about your spending</h2>
          <div className="chat-header-actions">{closeButton}</div>
        </div>
        <p className="message">
          Chat is unavailable: no OPENAI_API_KEY is configured for this server.
        </p>
      </section>
    )
  }

  return (
    <section className="chat-panel">
      <div className="chat-header">
        <h2>Ask about your spending</h2>
        <div className="chat-header-actions">
          <button
            type="button"
            className="chat-new-button"
            onClick={newChat}
            disabled={isStreaming || messages.length === 0}
          >
            New chat
          </button>
          {closeButton}
        </div>
      </div>

      <ul className="chat-messages" ref={listRef}>
        {messages.length === 0 && (
          <li className="chat-empty">Try: “How much did I spend on dining in July?”</li>
        )}
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </ul>

      {error && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}

      <form className="chat-composer" onSubmit={handleSubmit}>
        <label htmlFor={inputId}>Ask a question</label>
        <div className="chat-composer-row">
          <input
            id={inputId}
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask a question about your spending…"
            disabled={available === null || isStreaming}
          />
          <button type="submit" disabled={!draft.trim() || isStreaming || available === null}>
            {isStreaming ? 'Thinking…' : 'Send'}
          </button>
        </div>
      </form>
    </section>
  )
}
