import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchChatStatus } from '../api/financeApi'
import { streamChat } from '../api/streamChat'
import type { ChatMessage } from '../interfaces/chat'

const THREAD_ID_STORAGE_KEY = 'myfinance.chat.thread_id'

function loadOrCreateThreadId(): string {
  const stored = localStorage.getItem(THREAD_ID_STORAGE_KEY)
  if (stored) return stored
  const created = crypto.randomUUID()
  localStorage.setItem(THREAD_ID_STORAGE_KEY, created)
  return created
}

function describe(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Could not reach the server. Is the backend running?'
}

/** Owns the chat conversation: thread identity, messages, and the live stream. */
export function useChat() {
  const [threadId, setThreadId] = useState<string>(loadOrCreateThreadId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [available, setAvailable] = useState<boolean | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchChatStatus()
      .then((status) => {
        if (!cancelled) setAvailable(status.available)
      })
      .catch(() => {
        if (!cancelled) setAvailable(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Abort any in-flight stream when the panel unmounts.
  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isStreaming) return

      setError(null)
      const assistantId = crypto.randomUUID()
      setMessages((previous) => [
        ...previous,
        { id: crypto.randomUUID(), role: 'user', content: trimmed },
        { id: assistantId, role: 'assistant', content: '' },
      ])
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller
      try {
        for await (const event of streamChat(trimmed, threadId, controller.signal)) {
          if (event.type === 'token') {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + event.text }
                  : message,
              ),
            )
          } else if (event.type === 'error') {
            setError(event.detail)
          } else if (event.type === 'done') {
            break
          }
        }
      } catch (caught) {
        // An abort means "New chat" or unmount cancelled this on purpose, not
        // a failure worth showing the person.
        if (controller.signal.aborted) return
        setError(describe(caught))
      } finally {
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [isStreaming, threadId],
  )

  const newChat = useCallback(() => {
    abortRef.current?.abort()
    const created = crypto.randomUUID()
    localStorage.setItem(THREAD_ID_STORAGE_KEY, created)
    setThreadId(created)
    setMessages([])
    setError(null)
  }, [])

  return { messages, isStreaming, error, available, send, newChat }
}
