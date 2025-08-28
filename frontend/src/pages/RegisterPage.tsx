import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'

export default function RegisterPage() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/auth/register', { username, email, password })
      const { data } = await api.post('/api/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      nav('/')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Register failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white shadow rounded p-6 space-y-4">
        <h1 className="text-xl font-semibold">Register</h1>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <input className="w-full border rounded px-3 py-2" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className="w-full border rounded px-3 py-2" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="w-full border rounded px-3 py-2" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="w-full bg-blue-600 text-white py-2 rounded">Create account</button>
        <div className="text-sm">Have an account? <Link to="/login" className="text-blue-600">Login</Link></div>
      </form>
    </div>
  )
}


