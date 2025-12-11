import React, { useEffect, useState } from 'react'
import { Routes, Route, useNavigate, Link } from 'react-router-dom'
import Login from './pages/Login'
import { getProfile } from './api'

function Dashboard() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('access')
    if (!token) {
      navigate('/login')
      return
    }
    getProfile(token)
      .then((data) => setProfile(data))
      .catch(() => {
        setError('Session expired. Please login again.')
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        navigate('/login')
      })
  }, [navigate])

  const logout = () => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    navigate('/login')
  }

  return (
    <div style={{ maxWidth: 720, margin: '40px auto', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Leave Management Dashboard</h2>
        <button onClick={logout}>Logout</button>
      </div>
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      {!profile && !error && <div>Loading profile…</div>}
      {profile && (
        <div>
          <p>
            <b>Name:</b> {profile.first_name} {profile.last_name}
          </p>
          <p>
            <b>Role:</b> {profile.role}
          </p>
          <p>
            <b>Affiliate:</b> {typeof profile.affiliate === 'object' ? profile.affiliate?.name : profile.affiliate}
          </p>
          <p>
            <b>Department:</b>{' '}
            {profile.department
              ? typeof profile.department === 'object'
                ? profile.department?.name
                : profile.department
              : '—'}
          </p>
          <p>
            <Link to="/login">Switch account</Link>
          </p>
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<Dashboard />} />
    </Routes>
  )
}
