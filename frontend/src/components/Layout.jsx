import { NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

function BrandMark() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2.5L21 7v5.5c0 5.2-3.6 9.6-9 11-5.4-1.4-9-5.8-9-11V7l9-4.5z"
        stroke="#e2b03a"
        strokeWidth="1.5"
        fill="#1a2118"
      />
      <circle cx="12" cy="11.5" r="2.2" fill="#e2b03a" />
    </svg>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const data = await api.listNotifications(true)
        if (alive) setUnread(data.unreadCount || 0)
      } catch {
        /* ignore */
      }
    }
    load()
    const id = setInterval(load, 15000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <BrandMark />
          </div>
          <div className="brand-text">
            <strong>Sentinel</strong>
            <span>Command</span>
          </div>
        </div>

        <nav className="nav">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/cameras">Cameras</NavLink>
          <NavLink to="/users">Users</NavLink>
          <NavLink to="/alerts">Motion alerts</NavLink>
          <NavLink to="/notifications">
            Notifications
            {unread > 0 && <span className="badge">{unread}</span>}
          </NavLink>
        </nav>

        <div className="sidebar-foot">
          <div className="who">Signed in as {user?.username || 'admin'}</div>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet context={{ refreshUnread: async () => {
          const data = await api.listNotifications(true)
          setUnread(data.unreadCount || 0)
        } }} />
      </main>
    </div>
  )
}
