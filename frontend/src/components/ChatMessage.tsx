import type { ChatMessage as ChatMessageData } from '../interfaces/chat'

interface Props {
  message: ChatMessageData
}

/** One message bubble, from the person or the assistant. */
export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'
  return (
    <li className={`chat-message ${isUser ? 'chat-message-user' : 'chat-message-assistant'}`}>
      <span className="chat-message-role">{isUser ? 'You' : 'Assistant'}</span>
      <p className="chat-message-content">{message.content || '…'}</p>
    </li>
  )
}
