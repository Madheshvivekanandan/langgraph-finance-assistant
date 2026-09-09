export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
}

export interface ChatStatus {
  available: boolean
}

/** One parsed SSE frame from the chat stream. */
export type ChatStreamEvent =
  | { type: 'token'; text: string }
  | { type: 'error'; detail: string }
  | { type: 'done' }
