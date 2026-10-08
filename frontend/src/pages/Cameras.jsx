import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill'
import KeyReveal from '../components/KeyReveal'

export default function Cameras() {
  const [cameras, setCameras] = useState([])
  const [name, setName] = useState('')
  const [type, setType] = useState('facial')
  const [location, setLocation] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const data = await api.listCameras()
    setCameras(data.cameras || [])
  }, [])

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [load])

  const onCreate = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const data = await api.createCamera({ name, type, location })
      setAccessKey(data.accessKey || '')
      setName('')
      setLocation('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const onRevoke = async (id) => {
    setError('')
    try {
      await api.revokeCamera(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const onDelete = async (id) => {
    if (!confirm('Delete this camera permanently?')) return
    setError('')
    try {
      await api.deleteCamera(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Cameras</h1>
          <p>
            Create a camera to receive a one-time access key. Enter that key on the device to
            register it with Sentinel.
          </p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="grid split">
        <section className="panel">
          <div className="panel-title">
            <h2>Create camera</h2>
          </div>
          <form className="form-row" onSubmit={onCreate}>
            <label>
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Lobby facial cam"
                required
              />
            </label>
            <div className="form-row two">
              <label>
                Type
                <select value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="facial">Facial</option>
                  <option value="surveillance">Surveillance</option>
                </select>
              </label>
              <label>
                Location
                <input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Building A / door 2"
                />
              </label>
            </div>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Creating…' : 'Create & generate key'}
            </button>
          </form>
          <KeyReveal
            label="Camera access key"
            value={accessKey}
            onDismiss={() => setAccessKey('')}
          />
        </section>

        <section className="panel">
          <div className="panel-title">
            <h2>How pairing works</h2>
          </div>
          <ol style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--muted)', lineHeight: 1.6 }}>
            <li>Admin creates a facial or surveillance camera here.</li>
            <li>Copy the generated access key and give it to the device operator.</li>
            <li>
              Device calls <span className="mono">POST /api/cameras/claim</span> with that key.
            </li>
            <li>Status becomes active and the camera can talk to the server.</li>
          </ol>
        </section>
      </div>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <div className="panel-title">
          <h2>Registered cameras</h2>
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => load()}>
            Refresh
          </button>
        </div>
        {cameras.length === 0 ? (
          <div className="empty">No cameras yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Registered</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {cameras.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td className="mono">{c.type}</td>
                    <td>
                      <StatusPill status={c.status} />
                    </td>
                    <td>{c.location || '—'}</td>
                    <td className="mono">
                      {c.registeredAt ? new Date(c.registeredAt).toLocaleString() : '—'}
                    </td>
                    <td>
                      <div className="row-actions">
                        {c.status !== 'revoked' && (
                          <button
                            type="button"
                            className="btn btn-sm btn-ghost"
                            onClick={() => onRevoke(c.id)}
                          >
                            Revoke
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => onDelete(c.id)}
                        >
                          Delete
                        </button>
                      </div>
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
