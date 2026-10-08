import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Cameras from './pages/Cameras'
import Users from './pages/Users'
import Alerts from './pages/Alerts'
import Notifications from './pages/Notifications'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <div className="loading-screen">Loading Sentinel…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <Protected>
                <Layout />
              </Protected>
            }
          >
            <Route index element={<Overview />} />
            <Route path="cameras" element={<Cameras />} />
            <Route path="users" element={<Users />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="notifications" element={<Notifications />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
