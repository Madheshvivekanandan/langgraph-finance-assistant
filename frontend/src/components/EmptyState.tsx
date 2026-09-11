interface Props {
  title: string
  children?: React.ReactNode
  action?: React.ReactNode
}

/** Title, one line of explanation, at most one action (D2). */
export function EmptyState({ title, children, action }: Props) {
  return (
    <div className="empty-state">
      <h2 className="empty-state-title">{title}</h2>
      {children && <p className="message">{children}</p>}
      {action}
    </div>
  )
}
