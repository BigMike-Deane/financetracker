import { useState, useEffect } from 'react'
import { api, formatCurrency } from '../api'

function AccountsSummary({ accounts }) {
  const totals = accounts.reduce((acc, account) => {
    const balance = account.current_balance || 0
    const type = account.type

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

  return (
    <div className="card mb-4">
      <div className="text-dark-400 text-sm mb-3">Account Summary</div>

      {/* Net Worth */}
      <div className="text-center mb-4 pb-4 border-b border-dark-700">
        <div className="text-dark-400 text-xs uppercase tracking-wide">Net Worth</div>
        <div className="text-2xl font-bold text-white">{formatCurrency(netWorth)}</div>
      </div>

      {/* Assets */}
      <div className="grid grid-cols-2 gap-3 mb-3">
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
  )
}

function SimpleFINSetup({ onSuccess }) {
  const [setupToken, setSetupToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showInstructions, setShowInstructions] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!setupToken.trim()) {
      setError('Please enter a setup token')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await api.setupSimpleFIN(setupToken.trim())
      setSetupToken('')
      onSuccess(result)
    } catch (err) {
      setError(err.message || 'Failed to connect. Make sure your setup token is valid and has not been used before.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          value={setupToken}
          onChange={(e) => setSetupToken(e.target.value)}
          placeholder="Paste your SimpleFIN setup token"
          className="w-full px-4 py-3 bg-dark-700 rounded-xl border border-dark-600 focus:border-primary-500 focus:outline-none text-sm"
          disabled={loading}
        />

        {error && (
          <div className="text-red-400 text-sm px-1">{error}</div>
        )}

        <button
          type="submit"
          disabled={loading || !setupToken.trim()}
          className="w-full py-4 bg-primary-500 rounded-xl font-semibold text-white hover:bg-primary-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <svg className="animate-spin w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
              </svg>
              <span>Connect Accounts</span>
            </>
          )}
        </button>
      </form>

      <button
        onClick={() => setShowInstructions(!showInstructions)}
        className="w-full mt-3 text-sm text-primary-400 hover:text-primary-300"
      >
        {showInstructions ? 'Hide instructions' : 'How do I get a setup token?'}
      </button>

      {showInstructions && (
        <div className="mt-3 p-4 bg-dark-700 rounded-xl text-sm space-y-3">
          <p className="font-semibold text-white">Setup Instructions:</p>
          <ol className="list-decimal list-inside space-y-2 text-dark-300">
            <li>
              Go to{' '}
              <a
                href="https://beta-bridge.simplefin.org"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 underline"
              >
                SimpleFIN Bridge
              </a>
              {' '}and create an account ($15/year)
            </li>
            <li>Connect your bank accounts (Fidelity, checking, etc.)</li>
            <li>Go to "My Accounts" and click "Apps" section</li>
            <li>Click "New Connection" and name it "Finance Tracker"</li>
            <li>Click "Create Setup Token" and copy the token</li>
            <li>Paste the token above and click Connect</li>
          </ol>
          <p className="text-dark-400 text-xs mt-2">
            Note: Each setup token can only be used once. If you need to reconnect, generate a new token in SimpleFIN.
          </p>
        </div>
      )}
    </div>
  )
}

function RulesManager() {
  const [rules, setRules] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [testResults, setTestResults] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    match_field: 'any',
    match_type: 'contains',
    match_value: '',
    assign_category: '',
    priority: 0
  })

  useEffect(() => {
    fetchRules()
    fetchCategories()
  }, [])

  const fetchRules = async () => {
    try {
      const data = await api.getRules()
      setRules(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const data = await api.getCategories()
      setCategories(data)
    } catch (err) {
      console.error(err)
    }
  }

  const handleTest = async () => {
    if (!formData.match_value) return
    try {
      const result = await api.testRule({
        match_field: formData.match_field,
        match_type: formData.match_type,
        match_value: formData.match_value,
        limit: 5
      })
      setTestResults(result)
    } catch (err) {
      console.error(err)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name || !formData.match_value || !formData.assign_category) return

    try {
      await api.createRule(formData)
      setFormData({
        name: '',
        match_field: 'any',
        match_type: 'contains',
        match_value: '',
        assign_category: '',
        priority: 0
      })
      setShowForm(false)
      setTestResults(null)
      fetchRules()
    } catch (err) {
      console.error(err)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this rule?')) return
    try {
      await api.deleteRule(id)
      fetchRules()
    } catch (err) {
      console.error(err)
    }
  }

  const handleApply = async (id) => {
    try {
      const result = await api.applyRule(id)
      alert(`Applied to ${result.updated_count} transactions`)
    } catch (err) {
      console.error(err)
    }
  }

  const handleToggle = async (rule) => {
    try {
      await api.updateRule(rule.id, { is_active: !rule.is_active })
      fetchRules()
    } catch (err) {
      console.error(err)
    }
  }

  // Group categories by parent
  const groupedCategories = categories.reduce((acc, cat) => {
    if (!acc[cat.parent]) acc[cat.parent] = []
    acc[cat.parent].push(cat)
    return acc
  }, {})

  return (
    <div className="mb-6">
      <div className="flex justify-between items-center mb-2">
        <div className="text-dark-400 text-sm">Categorization Rules</div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm text-primary-500"
        >
          {showForm ? 'Cancel' : '+ Add Rule'}
        </button>
      </div>

      {/* Add Rule Form */}
      {showForm && (
        <div className="card mb-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-dark-400 text-xs block mb-1">Rule Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Costco Groceries"
                className="w-full px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-dark-400 text-xs block mb-1">Match Field</label>
                <select
                  value={formData.match_field}
                  onChange={(e) => setFormData({...formData, match_field: e.target.value})}
                  className="w-full px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none"
                >
                  <option value="any">Any Field</option>
                  <option value="name">Transaction Name</option>
                  <option value="merchant_name">Merchant Name</option>
                </select>
              </div>
              <div>
                <label className="text-dark-400 text-xs block mb-1">Match Type</label>
                <select
                  value={formData.match_type}
                  onChange={(e) => setFormData({...formData, match_type: e.target.value})}
                  className="w-full px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none"
                >
                  <option value="contains">Contains</option>
                  <option value="starts_with">Starts With</option>
                  <option value="ends_with">Ends With</option>
                  <option value="exact">Exact Match</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-dark-400 text-xs block mb-1">Match Pattern</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={formData.match_value}
                  onChange={(e) => setFormData({...formData, match_value: e.target.value})}
                  placeholder="e.g., COSTCO"
                  className="flex-1 px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
                <button
                  type="button"
                  onClick={handleTest}
                  className="px-3 py-2 bg-dark-600 rounded-lg text-sm hover:bg-dark-500"
                >
                  Test
                </button>
              </div>
            </div>

            {/* Test Results */}
            {testResults && (
              <div className="bg-dark-700 rounded-lg p-3 text-sm">
                <div className="text-dark-400 mb-2">
                  {testResults.match_count} matching transactions:
                </div>
                {testResults.matches.length > 0 ? (
                  <div className="space-y-1">
                    {testResults.matches.map(m => (
                      <div key={m.id} className="text-xs text-dark-300 truncate">
                        {m.date} - {m.name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-dark-500 text-xs">No matches found</div>
                )}
              </div>
            )}

            <div>
              <label className="text-dark-400 text-xs block mb-1">Assign Category</label>
              <select
                value={formData.assign_category}
                onChange={(e) => setFormData({...formData, assign_category: e.target.value})}
                className="w-full px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none"
              >
                <option value="">Select category...</option>
                {Object.entries(groupedCategories).map(([parent, cats]) => (
                  <optgroup key={parent} label={parent}>
                    {cats.map(cat => (
                      <option key={cat.value} value={cat.value}>
                        {cat.emoji} {cat.display}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={!formData.name || !formData.match_value || !formData.assign_category}
              className="w-full py-3 bg-primary-500 rounded-lg font-medium text-white hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              Create Rule
            </button>
          </form>
        </div>
      )}

      {/* Rules List */}
      {loading ? (
        <div className="skeleton h-20 rounded-xl" />
      ) : rules.length > 0 ? (
        <div className="space-y-2">
          {rules.map(rule => (
            <div key={rule.id} className={`card py-3 ${!rule.is_active ? 'opacity-50' : ''}`}>
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-medium text-sm">{rule.name}</div>
                  <div className="text-dark-400 text-xs mt-1">
                    If {rule.match_field === 'any' ? 'any field' : rule.match_field} {rule.match_type.replace('_', ' ')} "{rule.match_value}"
                  </div>
                  <div className="text-primary-400 text-xs mt-1">
                    → {rule.assign_category_display}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`p-1.5 rounded ${rule.is_active ? 'text-green-400' : 'text-dark-500'}`}
                    title={rule.is_active ? 'Disable' : 'Enable'}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleApply(rule.id)}
                    className="p-1.5 text-primary-400 rounded hover:bg-dark-700"
                    title="Apply to existing transactions"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="p-1.5 text-red-400 rounded hover:bg-dark-700"
                    title="Delete"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-4">
          <div className="text-dark-400 text-sm">No rules yet</div>
          <div className="text-dark-500 text-xs mt-1">Create rules to auto-categorize transactions</div>
        </div>
      )}
    </div>
  )
}

function InstitutionCard({ institution, onRemove, onSync }) {
  const [syncing, setSyncing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.syncInstitution(institution.id)
      onSync()
    } catch (err) {
      console.error(err)
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="card mb-3">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-xl bg-primary-500/20"
          >
            {institution.name === 'SimpleFIN Bridge' ? '🔗' : '🏦'}
          </div>
          <div>
            <div className="font-semibold">{institution.name}</div>
            <div className="text-dark-400 text-sm">
              {institution.accounts_count} account{institution.accounts_count !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${
            institution.sync_status === 'success' ? 'bg-green-500' :
            institution.sync_status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
          }`} />
          <span className="text-dark-400 text-xs">
            {institution.last_sync
              ? new Date(institution.last_sync).toLocaleDateString()
              : 'Never synced'}
          </span>
        </div>
      </div>

      <div className="flex gap-2 mt-3 pt-3 border-t border-dark-700">
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex-1 py-2 bg-dark-700 rounded-lg text-sm font-medium hover:bg-dark-600 transition-colors disabled:opacity-50"
        >
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
        <button
          onClick={() => onRemove(institution.id)}
          className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/30 transition-colors"
        >
          Remove
        </button>
      </div>
    </div>
  )
}

export default function Settings({ onLogout }) {
  const [institutions, setInstitutions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [successMessage, setSuccessMessage] = useState(null)

  const fetchData = async () => {
    try {
      const [instData, acctData] = await Promise.all([
        api.getInstitutions(),
        api.getAccounts()
      ])
      setInstitutions(instData)
      setAccounts(acctData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleConnectionSuccess = (result) => {
    setSuccessMessage(`Connected! Synced ${result.accounts_synced} accounts and ${result.transactions_synced} transactions.`)
    fetchData()
    setTimeout(() => setSuccessMessage(null), 5000)
  }

  const handleRemove = async (id) => {
    if (!confirm('Are you sure you want to remove this connection? All associated data will be deleted.')) {
      return
    }
    try {
      await api.removeInstitution(id)
      fetchData()
    } catch (err) {
      console.error(err)
    }
  }

  const handleSyncAll = async () => {
    setSyncing(true)
    try {
      await api.syncAll()
      await fetchData()
    } catch (err) {
      console.error(err)
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Settings</h1>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-4 p-4 bg-green-500/20 border border-green-500/30 rounded-xl text-green-400 text-sm">
          {successMessage}
        </div>
      )}

      {/* Account Summary */}
      {accounts.length > 0 && <AccountsSummary accounts={accounts} />}

      {/* Connect Account */}
      <div className="mb-6">
        <div className="text-dark-400 text-sm mb-2">Connect Bank Accounts</div>
        <SimpleFINSetup onSuccess={handleConnectionSuccess} />
      </div>

      {/* Connected Institutions */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <div className="text-dark-400 text-sm">Connected Accounts</div>
          {institutions.length > 0 && (
            <button
              onClick={handleSyncAll}
              disabled={syncing}
              className="text-sm text-primary-500 disabled:opacity-50"
            >
              {syncing ? 'Syncing...' : 'Sync All'}
            </button>
          )}
        </div>

        {loading ? (
          <>
            <div className="skeleton h-24 rounded-2xl mb-3" />
            <div className="skeleton h-24 rounded-2xl" />
          </>
        ) : institutions.length > 0 ? (
          institutions.map(inst => (
            <InstitutionCard
              key={inst.id}
              institution={inst}
              onRemove={handleRemove}
              onSync={fetchData}
            />
          ))
        ) : (
          <div className="card text-center py-6">
            <div className="text-dark-400">No accounts connected yet</div>
            <div className="text-dark-500 text-sm mt-1">Use SimpleFIN Bridge to connect your banks</div>
          </div>
        )}
      </div>

      {/* Categorization Rules */}
      <RulesManager />

      {/* App Info */}
      <div className="card">
        <div className="text-dark-400 text-sm mb-2">About</div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-dark-400">Version</span>
            <span>2.0.0</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dark-400">Bank Connection</span>
            <span>SimpleFIN Bridge</span>
          </div>
        </div>
      </div>

      {/* PWA Install Instructions */}
      <div className="mt-6 p-4 bg-primary-500/10 rounded-xl border border-primary-500/30">
        <div className="font-semibold text-primary-400 mb-2">Install App</div>
        <div className="text-sm text-dark-300 space-y-2">
          <p><strong>iOS:</strong> Tap Share then "Add to Home Screen"</p>
          <p><strong>Android:</strong> Tap Menu then "Install app" or "Add to Home screen"</p>
        </div>
      </div>

      {/* Logout Button */}
      {onLogout && (
        <button
          onClick={onLogout}
          className="mt-6 w-full py-3 bg-red-500/20 text-red-400 rounded-xl font-semibold hover:bg-red-500/30 transition-colors"
        >
          Sign Out
        </button>
      )}

      {/* Bottom spacer for nav clearance */}
      <div className="h-4" />
    </div>
  )
}
