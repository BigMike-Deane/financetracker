// API base URL - can be configured via environment variable for production
const API_BASE = import.meta.env.VITE_API_URL || '/api'

// Store credentials in memory (set via login)
let authCredentials = null

// Check if we have stored credentials in sessionStorage
try {
  const stored = sessionStorage.getItem('finance_auth')
  if (stored) {
    authCredentials = JSON.parse(stored)
  }
} catch (e) {
  // Ignore storage errors
}

export function setAuthCredentials(username, password) {
  authCredentials = { username, password }
  try {
    sessionStorage.setItem('finance_auth', JSON.stringify(authCredentials))
  } catch (e) {
    // Ignore storage errors
  }
}

export function clearAuthCredentials() {
  authCredentials = null
  try {
    sessionStorage.removeItem('finance_auth')
  } catch (e) {
    // Ignore storage errors
  }
}

export function hasAuthCredentials() {
  return authCredentials !== null
}

async function fetchAPI(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Add Basic Auth header if credentials are set
  if (authCredentials) {
    const credentials = btoa(`${authCredentials.username}:${authCredentials.password}`)
    headers['Authorization'] = `Basic ${credentials}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers,
    ...options,
  })

  // Handle 401 Unauthorized - clear credentials and throw specific error
  if (response.status === 401) {
    clearAuthCredentials()
    throw new Error('AUTH_REQUIRED')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

export const api = {
  // Dashboard
  getDashboard: () => fetchAPI('/dashboard'),

  // Institutions
  getInstitutions: () => fetchAPI('/institutions'),
  removeInstitution: (id) => fetchAPI(`/institutions/${id}`, { method: 'DELETE' }),

  // SimpleFIN
  setupSimpleFIN: (setupToken) =>
    fetchAPI('/simplefin/setup', {
      method: 'POST',
      body: JSON.stringify({ setup_token: setupToken }),
    }),

  // Sync
  syncAll: () => fetchAPI('/sync', { method: 'POST' }),
  syncInstitution: (id) => fetchAPI(`/sync/${id}`, { method: 'POST' }),

  // Accounts
  getAccounts: (includeHidden = false) =>
    fetchAPI(`/accounts?include_hidden=${includeHidden}`),
  updateAccount: (id, data) =>
    fetchAPI(`/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Transactions
  getTransactions: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value)
      }
    })
    return fetchAPI(`/transactions?${searchParams}`)
  },
  updateTransaction: (id, data) =>
    fetchAPI(`/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Net Worth
  getNetWorthHistory: (days = 30) => fetchAPI(`/net-worth/history?days=${days}`),

  // Spending
  getSpendingSummary: (startDate, endDate) => {
    const params = new URLSearchParams()
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    return fetchAPI(`/spending/summary?${params}`)
  },
  getSpendingTrends: (months = 6) => fetchAPI(`/spending/trends?months=${months}`),
  getSpendingTrendsByDays: (days = 30) => fetchAPI(`/spending/trends?days=${days}`),
  getSpendingByVendor: (startDate, endDate, limit = 15) => {
    const params = new URLSearchParams()
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    params.append('limit', limit)
    return fetchAPI(`/spending/by-vendor?${params}`)
  },

  // Holdings
  getHoldings: () => fetchAPI('/holdings'),

  // Categories
  getCategories: () => fetchAPI('/categories'),

  // Rules
  getRules: () => fetchAPI('/rules'),
  createRule: (data) => fetchAPI('/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) => fetchAPI(`/rules/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRule: (id) => fetchAPI(`/rules/${id}`, { method: 'DELETE' }),
  applyRule: (id) => fetchAPI(`/rules/${id}/apply`, { method: 'POST' }),
  testRule: (params) => {
    const searchParams = new URLSearchParams(params)
    return fetchAPI(`/rules/test?${searchParams}`)
  },

  // Subscriptions
  getSubscriptions: (includeDismissed = false) =>
    fetchAPI(`/subscriptions?include_dismissed=${includeDismissed}`),
  getSubscriptionSummary: () => fetchAPI('/subscriptions/summary'),
  detectSubscriptions: (days = 90) =>
    fetchAPI(`/subscriptions/detect?days=${days}`, { method: 'POST' }),
  createSubscription: (data) =>
    fetchAPI('/subscriptions', { method: 'POST', body: JSON.stringify(data) }),
  confirmSubscription: (data) => {
    const params = new URLSearchParams(data)
    return fetchAPI(`/subscriptions/confirm?${params}`, { method: 'POST' })
  },
  updateSubscription: (id, data) =>
    fetchAPI(`/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSubscription: (id, dismiss = false) =>
    fetchAPI(`/subscriptions/${id}?dismiss=${dismiss}`, { method: 'DELETE' }),
  getSubscriptionTransactions: (id) =>
    fetchAPI(`/subscriptions/${id}/transactions`),
  getPatternTransactions: (pattern) =>
    fetchAPI(`/subscriptions/pattern/${encodeURIComponent(pattern)}/transactions`),
}

// Format currency
export function formatCurrency(amount, showSign = false) {
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))

  if (showSign && amount !== 0) {
    return amount >= 0 ? `+${formatted}` : `-${formatted}`
  }
  return amount < 0 ? `-${formatted}` : formatted
}

// Format percentage
export function formatPercent(value, showSign = false) {
  const formatted = `${Math.abs(value).toFixed(1)}%`
  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`
  }
  return value < 0 ? `-${formatted}` : formatted
}

// Format date - parse as local timezone to avoid UTC offset issues
export function formatDate(dateStr) {
  if (!dateStr) return ''
  // Parse YYYY-MM-DD as local date, not UTC
  const [year, month, day] = dateStr.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
