import { useCallback, useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { api } from '../api/client'

export default function Notifications() {
  const { refreshUnread } = useOutletContext() || {}
  const [notifications, setNotifications] = useState([])
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    const data = await api.listNotifications(unreadOnly)
    setNotifications(data.notifications || [])
    if (refreshUnread) await refreshUnread()
  }, [unreadOnly, refreshUnread])

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [load])

  const markOne = async (id) => {
    await api.markRead(id)
    await load()
  }

  const markAll = async () => {
    setError('')
    try {
      await api.markAllRead()
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const clearAll = async () => {
    if (!confirm('Delete all notifications permanently?')) return
    setError('')
    try {
      await api.clearNotifications()
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Notifications</h1>
          <p>Enrollments, authorizations, camera claims, and motion events.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className={`btn btn-sm ${unreadOnly ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setUnreadOnly((v) => !v)}
          >
            {unreadOnly ? 'Unread only' : 'Show all'}
          </button>
          <button type="button" className="btn btn-sm btn-ghost" onClick={markAll}>
            Mark all read
          </button>
          <button type="button" className="btn btn-sm btn-danger" onClick={clearAll}>
            Clear all
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        {notifications.length === 0 ? (
          <div className="empty">No notifications.</div>
        ) : (
          <div className="notif-list">
            {notifications.map((n) => (
              <div key={n._id} className={`notif-item ${n.read ? '' : 'unread'}`}>
                <div className="meta">
                  <span className="mono">{n.type}</span>
                  <span>{new Date(n.createdAt).toLocaleString()}</span>
                </div>
                <strong>{n.title}</strong>
                <span style={{ color: 'var(--muted)' }}>{n.message}</span>
                {!n.read && (
                  <div style={{ marginTop: '0.4rem' }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={() => markOne(n._id)}
                    >
                      Mark read
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
