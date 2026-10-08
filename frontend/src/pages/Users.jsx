import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import StatusPill from '../components/StatusPill'
import KeyReveal from '../components/KeyReveal'

export default function Users() {
  const [users, setUsers] = useState([])
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [enrollKey, setEnrollKey] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const data = await api.listUsers()
    setUsers(data.users || [])
  }, [])

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [load])

  const onCreate = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const data = await api.createUser({ username, email, fullName })
      setEnrollKey(data.enrollKey || '')
      setUsername('')
      setEmail('')
      setFullName('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const onAuthorize = async (id) => {
    setError('')
    try {
      await api.authorizeUser(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const onRevoke = async (id) => {
    setError('')
    try {
      await api.revokeUser(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const onDelete = async (id) => {
    if (!confirm('Delete this user permanently?')) return
    setError('')
    try {
      await api.deleteUser(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p>
            Create a person remotely, send them an enroll key, then authorize them after they
            enroll at a facial camera.
          </p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <div className="panel-title">
          <h2>Create user</h2>
        </div>
        <form className="form-row" onSubmit={onCreate}>
          <div className="form-row two">
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="alice"
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alice@example.com"
                required
              />
            </label>
          </div>
          <label>
            Full name
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alice Example"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? 'Creating…' : 'Create & generate enroll key'}
          </button>
        </form>
        <KeyReveal
          label="User enroll key"
          value={enrollKey}
          onDismiss={() => setEnrollKey('')}
        />
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <div className="panel-title">
          <h2>Directory</h2>
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => load()}>
            Refresh
          </button>
        </div>
        {users.length === 0 ? (
          <div className="empty">No users yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Face</th>
                  <th>Enrolled</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.username}</strong>
                      {u.fullName ? (
                        <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                          {u.fullName}
                        </div>
                      ) : null}
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <StatusPill status={u.status} />
                    </td>
                    <td>{u.hasFace ? 'Yes' : '—'}</td>
                    <td className="mono">
                      {u.enrolledAt ? new Date(u.enrolledAt).toLocaleString() : '—'}
                    </td>
                    <td>
                      <div className="row-actions">
                        {u.status === 'enrolled' && (
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            onClick={() => onAuthorize(u.id)}
                          >
                            Authorize
                          </button>
                        )}
                        {u.status !== 'revoked' && (
                          <button
                            type="button"
                            className="btn btn-sm btn-ghost"
                            onClick={() => onRevoke(u.id)}
                          >
                            Revoke
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => onDelete(u.id)}
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
