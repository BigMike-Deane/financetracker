import { useState, useEffect } from 'react'
import { api, formatCurrency } from '../api'

function EditBalanceModal({ account, onClose, onSave }) {
  const [balance, setBalance] = useState(Math.abs(account.current_balance || 0).toString())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isDebt = ['credit', 'loan', 'mortgage'].includes(account.type)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const numBalance = parseFloat(balance)
      if (isNaN(numBalance)) {
        setError('Please enter a valid number')
        return
      }

      // For debt accounts, store as negative
      const finalBalance = isDebt ? -Math.abs(numBalance) : numBalance
      await api.updateAccount(account.id, { current_balance: finalBalance })
      onSave(account.id, finalBalance)
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to update balance')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-800 rounded-2xl p-4 max-w-sm w-full">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Update Balance</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="bg-dark-700 rounded-xl p-3 mb-4">
          <div className="font-medium">{account.name}</div>
          <div className="text-dark-400 text-sm">{account.institution_name}</div>
          <div className="text-dark-500 text-xs mt-1">
            Current: {formatCurrency(account.current_balance)}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="text-dark-400 text-sm block mb-2">
              {isDebt ? 'Amount Owed' : 'Current Balance'}
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400">$</span>
              <input
                type="number"
                step="0.01"
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
                className="w-full pl-8 pr-4 py-3 bg-dark-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="0.00"
                autoFocus
              />
            </div>
            {isDebt && (
              <div className="text-dark-500 text-xs mt-1">
                Enter as positive number (e.g., 500 for $500 owed)
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 bg-dark-700 rounded-xl font-medium hover:bg-dark-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-3 bg-primary-500 rounded-xl font-medium hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const typeConfig = {
  checking: { icon: '🏦', label: 'Checking', color: 'text-blue-400' },
  savings: { icon: '💰', label: 'Savings', color: 'text-green-400' },
  credit: { icon: '💳', label: 'Credit Card', color: 'text-purple-400' },
  investment: { icon: '📈', label: 'Investment', color: 'text-yellow-400' },
  brokerage: { icon: '📈', label: 'Brokerage', color: 'text-yellow-400' },
  retirement: { icon: '🏦', label: 'Retirement', color: 'text-orange-400' },
  loan: { icon: '📋', label: 'Loan', color: 'text-red-400' },
  mortgage: { icon: '🏠', label: 'Mortgage', color: 'text-red-400' },
  other: { icon: '💵', label: 'Other', color: 'text-gray-400' },
}

function AccountCard({ account, onToggleHidden, onEditBalance }) {
  const config = typeConfig[account.type] || typeConfig.other
  const isDebt = ['credit', 'loan', 'mortgage'].includes(account.type)

  return (
    <div className={`card mb-3 ${account.is_hidden ? 'opacity-50' : ''}`}>
      <div className="flex justify-between items-start">
        <div className="flex gap-3">
          <div className="text-2xl">{config.icon}</div>
          <div>
            <div className="font-semibold">{account.name}</div>
            <div className="text-dark-400 text-sm">{account.institution_name}</div>
            <div className={`text-xs ${config.color}`}>{config.label}</div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-xl font-bold ${isDebt && account.current_balance > 0 ? 'text-red-400' : ''}`}>
            {formatCurrency(account.current_balance)}
          </div>
          {account.available_balance !== null && account.available_balance !== account.current_balance && (
            <div className="text-dark-400 text-xs">
              Available: {formatCurrency(account.available_balance)}
            </div>
          )}
          {account.credit_limit && (
            <div className="text-dark-400 text-xs">
              Limit: {formatCurrency(account.credit_limit)}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-dark-700 flex justify-end gap-3">
        <button
          onClick={() => onEditBalance(account)}
          className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
        >
          Edit Balance
        </button>
        <button
          onClick={() => onToggleHidden(account.id, !account.is_hidden)}
          className="text-sm text-dark-400 hover:text-white transition-colors"
        >
          {account.is_hidden ? 'Show in Dashboard' : 'Hide from Dashboard'}
        </button>
      </div>
    </div>
  )
}

export default function Accounts() {
  const [loading, setLoading] = useState(true)
  const [accounts, setAccounts] = useState([])
  const [institutions, setInstitutions] = useState([])
  const [showHidden, setShowHidden] = useState(false)
  const [editingAccount, setEditingAccount] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [accts, insts] = await Promise.all([
        api.getAccounts(true),
        api.getInstitutions()
      ])
      setAccounts(accts)
      setInstitutions(insts)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleToggleHidden = async (accountId, isHidden) => {
    try {
      await api.updateAccount(accountId, { is_hidden: isHidden })
      setAccounts(prev =>
        prev.map(a => a.id === accountId ? { ...a, is_hidden: isHidden } : a)
      )
    } catch (err) {
      console.error(err)
    }
  }

  const handleBalanceUpdate = (accountId, newBalance) => {
    setAccounts(prev =>
      prev.map(a => a.id === accountId ? { ...a, current_balance: newBalance, available_balance: newBalance } : a)
    )
  }

  const filteredAccounts = showHidden
    ? accounts
    : accounts.filter(a => !a.is_hidden)

  // Group by type
  const grouped = filteredAccounts.reduce((acc, account) => {
    const type = account.type || 'other'
    if (!acc[type]) acc[type] = []
    acc[type].push(account)
    return acc
  }, {})

  // Calculate totals by category
  const totals = accounts
    .filter(a => !a.is_hidden)
    .reduce((acc, a) => {
      const balance = a.current_balance || 0
      const type = a.type

      if (type === 'checking' || type === 'savings') {
        acc.cash += balance
        acc.assets += balance
      } else if (type === 'investment' || type === 'brokerage') {
        acc.investments += balance
        acc.assets += balance
      } else if (type === 'retirement') {
        acc.retirement += balance
        acc.assets += balance
      } else if (type === 'credit') {
        acc.liabilities += Math.abs(balance)
      } else if (type === 'loan' || type === 'mortgage') {
        acc.liabilities += Math.abs(balance)
      }
      return acc
    }, { assets: 0, investments: 0, retirement: 0, cash: 0, liabilities: 0 })

  const netWorth = totals.assets - totals.liabilities

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton h-8 w-32 mb-4" />
        <div className="skeleton h-24 rounded-2xl mb-3" />
        <div className="skeleton h-24 rounded-2xl mb-3" />
        <div className="skeleton h-24 rounded-2xl" />
      </div>
    )
  }

  return (
    <>
      {/* Edit Balance Modal */}
      {editingAccount && (
        <EditBalanceModal
          account={editingAccount}
          onClose={() => setEditingAccount(null)}
          onSave={handleBalanceUpdate}
        />
      )}

    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Accounts</h1>

      {/* Summary */}
      <div className="card mb-4">
        {/* Net Worth */}
        <div className="text-center mb-4 pb-4 border-b border-dark-700">
          <div className="text-dark-400 text-xs uppercase tracking-wide">Net Worth</div>
          <div className="text-2xl font-bold text-white">{formatCurrency(netWorth)}</div>
        </div>

        {/* Assets vs Liabilities */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-dark-700/50 rounded-xl p-3">
            <div className="text-dark-400 text-xs">Total Assets</div>
            <div className="text-lg font-semibold text-green-400">{formatCurrency(totals.assets)}</div>
          </div>
          <div className="bg-dark-700/50 rounded-xl p-3">
            <div className="text-dark-400 text-xs">Total Liabilities</div>
            <div className="text-lg font-semibold text-red-400">{formatCurrency(totals.liabilities)}</div>
          </div>
        </div>

        {/* Breakdown */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-dark-400">Cash (Checking + Savings)</span>
            <span className="text-white">{formatCurrency(totals.cash)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dark-400">Investments</span>
            <span className="text-white">{formatCurrency(totals.investments)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dark-400">Retirement</span>
            <span className="text-white">{formatCurrency(totals.retirement)}</span>
          </div>
          <div className="flex justify-between pt-2 border-t border-dark-700">
            <span className="text-dark-400">Credit Cards</span>
            <span className="text-red-400">-{formatCurrency(totals.liabilities)}</span>
          </div>
        </div>
      </div>

      {/* Show hidden toggle */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-dark-400 text-sm">{filteredAccounts.length} accounts</span>
        <button
          onClick={() => setShowHidden(!showHidden)}
          className="text-sm text-primary-500"
        >
          {showHidden ? 'Hide Hidden' : 'Show Hidden'}
        </button>
      </div>

      {/* Connected Institutions */}
      {institutions.length > 0 && (
        <div className="mb-4">
          <div className="text-dark-400 text-sm mb-2">Connected Institutions</div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {institutions.map(inst => (
              <div
                key={inst.id}
                className="flex-shrink-0 px-3 py-2 bg-dark-700 rounded-lg flex items-center gap-2"
              >
                {inst.logo_url ? (
                  <img src={inst.logo_url} alt="" className="w-5 h-5 rounded" />
                ) : (
                  <span>🏦</span>
                )}
                <span className="text-sm">{inst.name}</span>
                <span className={`w-2 h-2 rounded-full ${inst.sync_status === 'success' ? 'bg-green-500' : inst.sync_status === 'error' ? 'bg-red-500' : 'bg-yellow-500'}`} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Accounts by Type */}
      {Object.entries(grouped).map(([type, accts]) => (
        <div key={type} className="mb-4">
          <div className="text-dark-400 text-sm mb-2 flex items-center gap-2">
            <span>{typeConfig[type]?.icon || '💵'}</span>
            <span>{typeConfig[type]?.label || type}</span>
            <span className="text-dark-500">({accts.length})</span>
          </div>
          {accts.map(account => (
            <AccountCard
              key={account.id}
              account={account}
              onToggleHidden={handleToggleHidden}
              onEditBalance={setEditingAccount}
            />
          ))}
        </div>
      ))}

      {accounts.length === 0 && (
        <div className="card text-center py-8">
          <div className="text-4xl mb-4">🏦</div>
          <div className="text-lg font-semibold mb-2">No accounts connected</div>
          <div className="text-dark-400 text-sm mb-4">
            Connect your bank accounts to start tracking
          </div>
        </div>
      )}

      {/* Bottom spacer for nav clearance */}
      <div className="h-4" />
    </div>
    </>
  )
}
