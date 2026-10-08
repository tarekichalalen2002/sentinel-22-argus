async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { message: text }
    }
  }

  if (!res.ok) {
    const err = new Error(data?.message || `Request failed (${res.status})`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  login: (username, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/auth/me'),

  listCameras: () => request('/api/cameras'),
  createCamera: (body) =>
    request('/api/cameras', { method: 'POST', body: JSON.stringify(body) }),
  revokeCamera: (id) =>
    request(`/api/cameras/${id}/revoke`, { method: 'POST' }),
  deleteCamera: (id) =>
    request(`/api/cameras/${id}`, { method: 'DELETE' }),

  listUsers: () => request('/api/users'),
  createUser: (body) =>
    request('/api/users', { method: 'POST', body: JSON.stringify(body) }),
  authorizeUser: (id) =>
    request(`/api/users/${id}/authorize`, { method: 'POST' }),
  revokeUser: (id) =>
    request(`/api/users/${id}/revoke`, { method: 'POST' }),
  deleteUser: (id) =>
    request(`/api/users/${id}`, { method: 'DELETE' }),

  listAlerts: (limit = 50) => request(`/api/alerts?limit=${limit}`),
  clearAlerts: () => request('/api/alerts', { method: 'DELETE' }),

  listNotifications: (unread = false) =>
    request(`/api/notifications${unread ? '?unread=1' : ''}`),
  markRead: (id) =>
    request(`/api/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () =>
    request('/api/notifications/read-all', { method: 'POST' }),
  clearNotifications: () =>
    request('/api/notifications', { method: 'DELETE' }),
}
