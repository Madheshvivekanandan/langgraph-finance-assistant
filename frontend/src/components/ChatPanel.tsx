import { useEffect, useId, useRef, useState } from 'react'
import { useChat } from '../hooks/useChat'
import { ChatMessage } from './ChatMessage'

/**
 * Ask questions about the stored transactions, answered by the chat agent and
 * streamed token by token. A status gate gets out of the way before anyone
 * types, rather than failing after the fact.
 */
export function ChatPanel() {
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

  if (available === false) {
    return (
      <div className="panel">
        <h2>Ask about your spending</h2>
        <p className="message">
          Chat is unavailable: no OPENAI_API_KEY is configured for this server.
        </p>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="chat-header">
        <h2>Ask about your spending</h2>
        <button
          type="button"
          className="chat-new-button"
          onClick={newChat}
          disabled={isStreaming || messages.length === 0}
        >
          New chat
        </button>
      </div>

      {messages.length === 0 && (
        <p className="message">Try: “How much did I spend on dining in July?”</p>
      )}

      <ul className="chat-messages" ref={listRef}>
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
    </div>
  )
}
