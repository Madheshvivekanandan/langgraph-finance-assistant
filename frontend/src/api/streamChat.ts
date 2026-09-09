import type { ChatStreamEvent } from '../interfaces/chat'
import { API_BASE, toApiError } from './financeApi'

/**
 * Stream one chat turn as parsed SSE events.
 *
 * A POST, not `EventSource`: `EventSource` can only GET, which would put the
 * person's question in the URL and every access log. Reads the response body
 * with `getReader()` and a small line parser instead.
 */
export async function* streamChat(
  message: string,
  threadId: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
  })
  if (!response.ok) throw await toApiError(response)
  if (!response.body) return

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE frames are separated by a blank line; a frame may arrive split
      // across chunks, so only complete frames are consumed from the buffer.
      let frameEnd = buffer.indexOf('\n\n')
      while (frameEnd !== -1) {
        const frame = buffer.slice(0, frameEnd)
        buffer = buffer.slice(frameEnd + 2)
        const event = parseFrame(frame)
        if (event) yield event
        frameEnd = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}

function parseFrame(frame: string): ChatStreamEvent | null {
  let eventName: string | null = null
  let data: string | null = null
  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) eventName = line.slice('event: '.length)
    else if (line.startsWith('data: ')) data = line.slice('data: '.length)
  }
  if (!eventName || data === null) return null

  // The payload is always JSON - see backend/app/api/sse.py: a raw newline in
  // a token written unescaped would terminate the frame early.
  const payload: unknown = JSON.parse(data)
  if (typeof payload !== 'object' || payload === null) return null
  const record = payload as Record<string, unknown>

  if (eventName === 'token' && typeof record.text === 'string') {
    return { type: 'token', text: record.text }
  }
  if (eventName === 'error') {
    const detail = typeof record.detail === 'string' ? record.detail : 'Something went wrong.'
    return { type: 'error', detail }
  }
  if (eventName === 'done') {
    return { type: 'done' }
  }
  return null
}
