import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill'

function timeAgo(iso) {
  if (!iso) return '—'
  const ms = Date.now() - new Date(iso).getTime()
  const m = Math.floor(ms / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function Overview() {
  const [cameras, setCameras] = useState([])
  const [users, setUsers] = useState([])
  const [alerts, setAlerts] = useState([])
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [c, u, a, n] = await Promise.all([
          api.listCameras(),
          api.listUsers(),
          api.listAlerts(8),
          api.listNotifications(),
        ])
        if (!alive) return
        setCameras(c.cameras || [])
        setUsers(u.users || [])
        setAlerts(a.alerts || [])
        setNotifications(n.notifications || [])
      } catch (err) {
        if (alive) setError(err.message)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const activeCams = cameras.filter((c) => c.status === 'active').length
  const pendingCams = cameras.filter((c) => c.status === 'pending').length
  const authorized = users.filter((u) => u.status === 'authorized').length
  const awaitingAuth = users.filter((u) => u.status === 'enrolled').length
  const unread = notifications.filter((n) => !n.read).length

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Overview</h1>
          <p>Live posture of cameras, enrolled people, and motion events.</p>
        </div>
        <Link className="btn btn-primary" to="/cameras">
          Add camera
        </Link>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="grid stats">
        <div className="panel stat">
          <div className="label">Active cameras</div>
          <div className="value">{activeCams}</div>
          <div className="hint">{pendingCams} awaiting claim</div>
        </div>
        <div className="panel stat">
          <div className="label">Authorized users</div>
          <div className="value">{authorized}</div>
          <div className="hint">{awaitingAuth} enrolled, need approval</div>
        </div>
        <div className="panel stat">
          <div className="label">Unread alerts</div>
          <div className="value">{unread}</div>
          <div className="hint">Notifications queue</div>
        </div>
        <div className="panel stat">
          <div className="label">Recent motion</div>
          <div className="value">{alerts.length}</div>
          <div className="hint">Last batch loaded</div>
        </div>
      </div>

      <div className="grid split">
        <section className="panel">
          <div className="panel-title">
            <h2>Latest motion</h2>
            <Link className="btn btn-sm btn-ghost" to="/alerts">
              View all
            </Link>
          </div>
          {alerts.length === 0 ? (
            <div className="empty">No motion alerts yet.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Camera</th>
                    <th>Category</th>
                    <th>Label</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a._id}>
                      <td className="mono">{timeAgo(a.createdAt)}</td>
                      <td>{a.camera?.name || '—'}</td>
                      <td>
                        <StatusPill status={a.category} />
                      </td>
                      <td>{a.label || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-title">
            <h2>Needs attention</h2>
            <Link className="btn btn-sm btn-ghost" to="/notifications">
              Inbox
            </Link>
          </div>
          {notifications.filter((n) => !n.read).slice(0, 6).length === 0 ? (
            <div className="empty">You&apos;re caught up.</div>
          ) : (
            <div className="notif-list">
              {notifications
                .filter((n) => !n.read)
                .slice(0, 6)
                .map((n) => (
                  <div key={n._id} className="notif-item unread">
                    <strong>{n.title}</strong>
                    <span style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>{n.message}</span>
                    <div className="meta">
                      <span>{n.type}</span>
                      <span>{timeAgo(n.createdAt)}</span>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
