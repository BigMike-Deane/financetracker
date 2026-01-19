import { useState } from 'react'
import { setAuthCredentials } from '../api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Set credentials
      setAuthCredentials(username, password)

      // Test the credentials by making a simple API call
      const response = await fetch('/api/institutions', {
        headers: {
          'Authorization': `Basic ${btoa(`${username}:${password}`)}`
        }
      })

      if (response.status === 401) {
        setError('Invalid username or password')
        setLoading(false)
        return
      }

      if (!response.ok) {
        throw new Error('Connection failed')
      }

      // Credentials work, notify parent
      onLogin()
    } catch (err) {
      setError(err.message || 'Failed to connect')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-dark-900">
      <div className="card w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">💰</div>
          <h1 className="text-xl font-bold">Finance Tracker</h1>
          <p className="text-dark-400 text-sm">Sign in to access your finances</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-900/30 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm text-dark-400 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-dark-700 rounded-xl border border-dark-600 focus:border-primary-500 focus:outline-none"
              required
              autoComplete="username"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-dark-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-dark-700 rounded-xl border border-dark-600 focus:border-primary-500 focus:outline-none"
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-primary-500 hover:bg-primary-600 rounded-xl font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
