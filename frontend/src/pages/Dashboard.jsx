import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api, formatCurrency, formatPercent, APIError } from '../api'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import PullToRefresh from '../components/PullToRefresh'
import { useToast } from '../components/Toast'

function NetWorthCard({ data, history }) {
  const isPositive = data.change >= 0

  return (
    <div className="card mb-4">
      <div className="text-dark-400 text-sm mb-1">Net Worth</div>
      <div className="text-3xl font-bold mb-1">
        {formatCurrency(data.current)}
      </div>
      <div className={`text-sm flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
        <span>{isPositive ? '↑' : '↓'}</span>
        <span>{formatCurrency(data.change, true)}</span>
        <span className="text-dark-500">({formatPercent(data.change_pct, true)})</span>
      </div>

      {history && history.length > 1 && (
        <div className="mt-4 h-24 -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <Line
                type="monotone"
                dataKey="net_worth"
                stroke={isPositive ? '#34c759' : '#ff3b30'}
                strokeWidth={2}
                dot={false}
              />
              <Tooltip
                contentStyle={{ background: '#2c2c2e', border: 'none', borderRadius: '8px' }}
                labelStyle={{ color: '#8e8e93' }}
                formatter={(value) => [formatCurrency(value), 'Net Worth']}
                labelFormatter={(label) => { const [y,m,d] = label.split('-').map(Number); return new Date(y,m-1,d).toLocaleDateString() }}
              />
              <XAxis dataKey="date" hide />
              <YAxis hide domain={['dataMin - 1000', 'dataMax + 1000']} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-dark-700">
        <div>
          <div className="text-dark-400 text-xs">Cash</div>
          <div className="font-semibold">{formatCurrency(data.breakdown?.cash || 0)}</div>
          {data.breakdown?.cash_change !== 0 && (
            <div className={`text-xs ${data.breakdown?.cash_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {data.breakdown?.cash_change >= 0 ? '↑' : '↓'} {formatPercent(Math.abs(data.breakdown?.cash_change_pct || 0))}
            </div>
          )}
        </div>
        <div>
          <div className="text-dark-400 text-xs">Investments</div>
          <div className="font-semibold">{formatCurrency(data.breakdown?.investments || 0)}</div>
          {data.breakdown?.investments_change !== 0 && (
            <div className={`text-xs ${data.breakdown?.investments_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {data.breakdown?.investments_change >= 0 ? '↑' : '↓'} {formatPercent(Math.abs(data.breakdown?.investments_change_pct || 0))}
            </div>
          )}
        </div>
        <div>
          <div className="text-dark-400 text-xs">Retirement</div>
          <div className="font-semibold">{formatCurrency(data.breakdown?.retirement || 0)}</div>
          {data.breakdown?.retirement_change !== 0 && (
            <div className={`text-xs ${data.breakdown?.retirement_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {data.breakdown?.retirement_change >= 0 ? '↑' : '↓'} {formatPercent(Math.abs(data.breakdown?.retirement_change_pct || 0))}
            </div>
          )}
        </div>
        <div>
          <div className="text-dark-400 text-xs">Credit Cards</div>
          <div className="font-semibold text-red-400">
            {formatCurrency(data.breakdown?.credit_debt || 0)}
          </div>
          {data.breakdown?.credit_change !== 0 && (
            <div className={`text-xs ${data.breakdown?.credit_change <= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {data.breakdown?.credit_change <= 0 ? '↓' : '↑'} {formatPercent(Math.abs(data.breakdown?.credit_change_pct || 0))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AccountsList({ accounts }) {
  const accountTypes = Object.entries(accounts || {})

  if (accountTypes.length === 0) {
    return (
      <div className="card mb-4">
        <div className="text-center py-4">
          <div className="text-3xl mb-3">🏦</div>
          <div className="font-semibold mb-1">Connect Your Accounts</div>
          <div className="text-dark-400 text-sm mb-4">
            Link your bank accounts through SimpleFIN to start tracking your finances automatically.
          </div>
          <Link
            to="/settings"
            className="inline-block px-6 py-3 bg-primary-500 hover:bg-primary-600 rounded-xl font-semibold transition-colors"
          >
            Get Started
          </Link>
        </div>
      </div>
    )
  }

  const typeIcons = {
    checking: '🏦',
    savings: '💰',
    credit: '💳',
    investment: '📈',
    brokerage: '📈',
    retirement: '🏦',
    loan: '📋',
    mortgage: '🏠',
  }

  return (
    <div className="card mb-4">
      <div className="flex justify-between items-center mb-3">
        <div className="font-semibold">Accounts</div>
        <Link to="/accounts" className="text-primary-500 text-sm">See All</Link>
      </div>

      <div className="space-y-3">
        {accountTypes.slice(0, 2).map(([type, accts]) => (
          <div key={type}>
            {accts.slice(0, 3).map(account => (
              <div key={account.id} className="flex justify-between items-center py-2 border-b border-dark-700 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{typeIcons[type] || '🏦'}</span>
                  <div>
                    <div className="font-medium text-sm">{account.name}</div>
                    <div className="text-dark-400 text-xs">{account.institution}</div>
                  </div>
                </div>
                <div className={`font-semibold ${account.balance < 0 ? 'text-red-400' : ''}`}>
                  {formatCurrency(account.balance)}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function SpendingCard({ spending }) {
  const today = new Date()
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate()
  const dayOfMonth = today.getDate()
  const daysRemaining = daysInMonth - dayOfMonth

  // Use dynamic budget from API (75% of 3-month avg income) or fall back to default
  const budget = spending.budget || 4000
  const percentSpent = budget > 0 ? (spending.month_total / budget) * 100 : 0

  return (
    <div className="card mb-4">
      <div className="flex justify-between items-center mb-3">
        <div className="font-semibold">This Month</div>
        <Link to="/transactions" className="text-primary-500 text-sm">Details</Link>
      </div>

      <div className="mb-3">
        <div className="flex justify-between text-sm mb-1">
          <span>Spent</span>
          <span>{formatCurrency(spending.month_total)}</span>
        </div>
        <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${percentSpent > 100 ? 'bg-red-500' : percentSpent > 80 ? 'bg-yellow-500' : 'bg-green-500'}`}
            style={{ width: `${Math.min(percentSpent, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-dark-400 mt-1">
          <span>{daysRemaining} days left</span>
          <span>Budget: {formatCurrency(budget)}</span>
        </div>
      </div>

      <div className="space-y-2">
        {spending.by_category?.slice(0, 5).map(cat => (
          <div key={cat.category} className="flex justify-between items-center text-sm">
            <div className="flex items-center gap-2">
              <span>{cat.emoji}</span>
              <span>{cat.display}</span>
            </div>
            <span className="font-medium">{formatCurrency(cat.amount)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecentTransactions({ transactions }) {
  if (!transactions || transactions.length === 0) {
    return null
  }

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-3">
        <div className="font-semibold">Recent Activity</div>
        <Link to="/transactions" className="text-primary-500 text-sm">See All</Link>
      </div>

      <div className="space-y-3">
        {transactions.slice(0, 5).map(txn => (
          <div key={txn.id} className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-xl">{txn.category_emoji}</span>
              <div>
                <div className="font-medium text-sm">{txn.merchant_name || txn.name}</div>
                <div className="text-dark-400 text-xs">{txn.date}</div>
              </div>
            </div>
            <div className={`font-semibold ${txn.amount > 0 ? 'text-green-400' : ''}`}>
              {txn.amount > 0 ? '+' : ''}{formatCurrency(txn.amount)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ConnectionStatus({ institutions }) {
  if (!institutions || institutions.length === 0) {
    return null
  }

  const getStatusInfo = (inst) => {
    const isStale = inst.hours_since_sync > 24
    const isError = inst.sync_status === 'error'
    const isSuccess = inst.sync_status === 'success' && !isStale

    if (isError) {
      return { color: 'text-red-400', bg: 'bg-red-500', icon: '!', label: 'Error' }
    }
    if (isStale) {
      return { color: 'text-yellow-400', bg: 'bg-yellow-500', icon: '!', label: 'Stale' }
    }
    if (isSuccess) {
      return { color: 'text-green-400', bg: 'bg-green-500', icon: '✓', label: 'OK' }
    }
    return { color: 'text-dark-400', bg: 'bg-dark-500', icon: '?', label: 'Pending' }
  }

  const formatLastSync = (hours) => {
    if (hours == null) return 'Never'
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${Math.round(hours)}h ago`
    return `${Math.round(hours / 24)}d ago`
  }

  return (
    <div className="card mt-4">
      <div className="font-semibold mb-3">Connections</div>
      <div className="space-y-2">
        {institutions.map(inst => {
          const status = getStatusInfo(inst)
          return (
            <div key={inst.id} className="flex justify-between items-center py-2 border-b border-dark-700 last:border-0">
              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full ${status.bg} flex items-center justify-center text-xs font-bold text-white`}>
                  {status.icon}
                </div>
                <div>
                  <div className="font-medium text-sm">{inst.name}</div>
                  <div className="text-dark-400 text-xs">
                    {inst.accounts_count} account{inst.accounts_count !== 1 ? 's' : ''}
                    {' • '}
                    {formatLastSync(inst.hours_since_sync)}
                  </div>
                </div>
              </div>
              <div className={`text-xs font-medium ${status.color}`}>
                {status.label}
              </div>
            </div>
          )
        })}
      </div>
      {institutions.some(i => i.sync_status === 'error') && (
        <div className="mt-3 p-2 bg-red-900/30 rounded-lg">
          <div className="text-red-400 text-xs">
            {institutions.find(i => i.sync_status === 'error')?.error_message || 'Sync failed - try again or reconnect'}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [transactions, setTransactions] = useState([])
  const [institutions, setInstitutions] = useState([])
  const [syncing, setSyncing] = useState(false)
  const toast = useToast()

  const fetchData = async () => {
    try {
      setLoading(true)
      const [dashboard, nwHistory, txnData, instData] = await Promise.all([
        api.getDashboard(),
        api.getNetWorthHistory(30),
        api.getTransactions({ limit: 5 }),
        api.getInstitutions()
      ])
      setData(dashboard)
      setHistory(nwHistory)
      setTransactions(txnData.transactions)
      setInstitutions(instData)
      setError(null)
    } catch (err) {
      if (err instanceof APIError) {
        toast.showAPIError(err)
      } else {
        toast.showError(err.message || 'Failed to load data')
      }
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.syncAll()
      await fetchData()
      toast.showSuccess('Accounts synced successfully')
    } catch (err) {
      if (err instanceof APIError) {
        toast.showAPIError(err)
      } else {
        toast.showError(err.message || 'Sync failed')
      }
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton h-8 w-48 mb-4" />
        <div className="skeleton h-48 rounded-2xl mb-4" />
        <div className="skeleton h-32 rounded-2xl mb-4" />
        <div className="skeleton h-48 rounded-2xl" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="card bg-red-900/30 border border-red-500/30">
          <div className="text-red-400 font-semibold mb-2">Error loading data</div>
          <div className="text-sm text-dark-300 mb-4">{error}</div>
          <button
            onClick={fetchData}
            className="w-full py-2 bg-red-500 rounded-lg font-medium"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <PullToRefresh onRefresh={fetchData}>
      <div className="p-4">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
        <div>
          <div className="text-dark-400 text-sm">Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}</div>
          <h1 className="text-xl font-bold">Your Finances</h1>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="p-2 rounded-full bg-dark-700 hover:bg-dark-600 transition-colors disabled:opacity-50"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
        </button>
      </div>

      {/* Net Worth */}
      {data?.net_worth && (
        <NetWorthCard data={data.net_worth} history={history} />
      )}

      {/* Accounts */}
      <AccountsList accounts={data?.accounts} />

      {/* Spending */}
      {data?.spending && (
        <SpendingCard spending={data.spending} />
      )}

      {/* Recent Transactions */}
      <RecentTransactions transactions={transactions} />

      {/* Connection Status */}
      <ConnectionStatus institutions={institutions} />

        {/* Bottom spacer for nav clearance */}
        <div className="h-4" />
      </div>
    </PullToRefresh>
  )
}
