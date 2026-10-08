import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    const data = await api.listAlerts(100)
    setAlerts(data.alerts || [])
  }, [])

  useEffect(() => {
    load().catch((err) => setError(err.message))
    const id = setInterval(() => {
      load().catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [load])

  const clearAll = async () => {
    if (!confirm('Delete all motion alerts permanently?')) return
    setError('')
    try {
      await api.clearAlerts()
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Motion alerts</h1>
          <p>
            Surveillance cameras report moving objects classified as human, animal, or unknown
            object.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-ghost" onClick={() => load()}>
            Refresh
          </button>
          <button type="button" className="btn btn-danger" onClick={clearAll}>
            Clear all
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        {alerts.length === 0 ? (
          <div className="empty">No motion events yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Camera</th>
                  <th>Category</th>
                  <th>Label</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a._id}>
                    <td className="mono">{new Date(a.createdAt).toLocaleString()}</td>
                    <td>{a.camera?.name || '—'}</td>
                    <td>
                      <StatusPill status={a.category} />
                    </td>
                    <td>{a.label || '—'}</td>
                    <td className="mono">
                      {typeof a.confidence === 'number' ? a.confidence.toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
