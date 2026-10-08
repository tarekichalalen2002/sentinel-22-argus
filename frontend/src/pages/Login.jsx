import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { user, loading, login } = useAuth()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!loading && user) {
    return <Navigate to="/" replace />
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
              <path
                d="M12 2.5L21 7v5.5c0 5.2-3.6 9.6-9 11-5.4-1.4-9-5.8-9-11V7l9-4.5z"
                stroke="#e2b03a"
                strokeWidth="1.5"
                fill="#1a2118"
              />
              <circle cx="12" cy="11.5" r="2.2" fill="#e2b03a" />
            </svg>
          </div>
          <div className="brand-text">
            <strong>Sentinel</strong>
            <span>Admin access</span>
          </div>
        </div>

        <h1>Watch the perimeter</h1>
        <p className="sub">Sign in to manage cameras, enrollments, and motion alerts.</p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={onSubmit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
