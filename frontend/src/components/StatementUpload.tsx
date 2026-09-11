import { useId, useRef, useState } from 'react'
import { ApiError, uploadStatement } from '../api/financeApi'
import type { Statement } from '../interfaces/statement'

interface Props {
  onUploaded: (statement: Statement) => void
}

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'error'; message: string }

export function StatementUpload({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [upload, setUpload] = useState<UploadState>({ status: 'idle' })
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)

  const isUploading = upload.status === 'uploading'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!file || isUploading) return

    setUpload({ status: 'uploading' })
    try {
      const statement = await uploadStatement(file)
      onUploaded(statement)
      setUpload({ status: 'idle' })
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Could not reach the server. Is the backend running?'
      setUpload({ status: 'error', message })
    }
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2>Upload a statement</h2>
      {/* Still a real file input with a real label - no custom widget, no
          drag-and-drop in this pass. The dashed border is the only new thing. */}
      <div className="dropzone">
        <label htmlFor={inputId}>Bank statement (CSV)</label>
        <div className="upload-row">
          <input
            id={inputId}
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            aria-describedby={upload.status === 'error' ? `${inputId}-error` : undefined}
          />
          <button type="submit" disabled={!file || isUploading}>
            {isUploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </div>
      {upload.status === 'error' && (
        <p className="message message-error" id={`${inputId}-error`} role="alert">
          {upload.message}
        </p>
      )}
    </form>
  )
}
