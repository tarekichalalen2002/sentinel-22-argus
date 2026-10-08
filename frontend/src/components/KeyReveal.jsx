import { useState } from 'react'

export default function KeyReveal({ label, value, onDismiss }) {
  const [copied, setCopied] = useState(false)

  if (!value) return null

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="key-box">
      <div className="label">{label} — copy now; it won’t be shown again</div>
      <code>{value}</code>
      <div className="actions">
        <button type="button" className="btn btn-sm btn-primary" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
        {onDismiss && (
          <button type="button" className="btn btn-sm btn-ghost" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  )
}
