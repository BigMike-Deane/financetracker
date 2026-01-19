import { useState, useEffect, useCallback } from 'react'
import { api, formatCurrency } from '../api'
import PullToRefresh from '../components/PullToRefresh'

function TransactionHistoryModal({ subscription, transactions, loading, onClose }) {
  if (!subscription) return null

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end justify-center sm:items-center">
      <div className="bg-dark-800 w-full max-w-lg max-h-[80vh] rounded-t-2xl sm:rounded-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🔁</span>
            <div>
              <div className="font-semibold">{subscription.name}</div>
              <div className="text-dark-400 text-sm">
                {transactions.length} transactions
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-dark-700 rounded-full transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Transaction List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="skeleton h-16 rounded-xl" />
              ))}
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center text-dark-400 py-8">
              No transactions found
            </div>
          ) : (
            <div className="space-y-2">
              {transactions.map(txn => (
                <div
                  key={txn.id}
                  className="bg-dark-700/50 rounded-xl p-3 flex justify-between items-center"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">
                      {txn.merchant_name || txn.name}
                    </div>
                    <div className="text-dark-400 text-xs flex gap-2">
                      <span>{txn.date ? (() => { const [y,m,d] = txn.date.split('-').map(Number); return new Date(y,m-1,d).toLocaleDateString() })() : 'Pending'}</span>
                      <span>•</span>
                      <span className="truncate">{txn.account_name}</span>
                    </div>
                  </div>
                  <div className="font-semibold ml-3">
                    {formatCurrency(txn.amount)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SubscriptionCard({ subscription, onClick, onDelete }) {
  const cycleLabel = {
    weekly: '/wk',
    biweekly: '/2wk',
    monthly: '/mo',
    quarterly: '/qtr',
    semiannual: '/6mo',
    annual: '/yr'
  }

  const formatNextCharge = (daysUntil) => {
    if (daysUntil === 0) return 'Today'
    if (daysUntil === 1) return 'Tomorrow'
    if (daysUntil <= 7) return `In ${daysUntil} days`
    if (daysUntil <= 14) return 'Next week'
    if (daysUntil <= 30) return `In ${Math.ceil(daysUntil / 7)} weeks`
    return `In ${Math.round(daysUntil / 30)} mo`
  }

  const isUpcomingSoon = subscription.days_until_charge <= 7

  return (
    <div
      className="card flex justify-between items-center py-3 mb-2 cursor-pointer hover:bg-dark-700/50 transition-colors"
      onClick={() => onClick(subscription)}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">🔁</span>
        <div>
          <div className="font-medium">{subscription.name}</div>
          <div className="text-dark-400 text-xs flex flex-wrap gap-x-2">
            <span>{subscription.billing_cycle}</span>
            {subscription.days_until_charge !== undefined && (
              <span className={isUpcomingSoon ? 'text-yellow-400' : ''}>
                • {formatNextCharge(subscription.days_until_charge)}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="text-right">
          <div className="font-semibold">
            {formatCurrency(subscription.expected_amount)}{cycleLabel[subscription.billing_cycle] || '/mo'}
          </div>
          {subscription.monthly_equivalent && subscription.billing_cycle !== 'monthly' && (
            <div className="text-dark-500 text-xs">
              {formatCurrency(subscription.monthly_equivalent)}/mo
            </div>
          )}
          {subscription.amount_changed && (
            <div className="text-yellow-500 text-xs">Amount changed</div>
          )}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(subscription.id); }}
          className="p-1 text-dark-400 hover:text-red-400 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}

function DetectedSubscriptionCard({ subscription, onClick, onConfirm, onDismiss }) {
  const cycleLabel = {
    weekly: '/wk',
    biweekly: '/2wk',
    monthly: '/mo',
    quarterly: '/qtr',
    semiannual: '/6mo',
    annual: '/yr'
  }

  return (
    <div className="card py-3 mb-2">
      <div
        className="flex justify-between items-center mb-2 cursor-pointer"
        onClick={() => onClick(subscription)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">❓</span>
          <div>
            <div className="font-medium">{subscription.merchant}</div>
            <div className="text-dark-400 text-xs">
              {subscription.transaction_count} charges • {subscription.billing_cycle}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-semibold">
            ~{formatCurrency(subscription.amount)}{cycleLabel[subscription.billing_cycle] || '/mo'}
          </div>
          <div className="text-dark-400 text-xs">
            Tap to see history
          </div>
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={(e) => { e.stopPropagation(); onConfirm(subscription); }}
          className="flex-1 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors"
        >
          Confirm
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(subscription); }}
          className="flex-1 py-2 bg-dark-600 hover:bg-dark-500 rounded-lg font-medium transition-colors"
        >
          Not a Subscription
        </button>
      </div>
    </div>
  )
}

function AddSubscriptionModal({ onClose, onAdd }) {
  const [name, setName] = useState('')
  const [merchantPattern, setMerchantPattern] = useState('')
  const [amount, setAmount] = useState('')
  const [billingCycle, setBillingCycle] = useState('monthly')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name || !amount) return

    setLoading(true)
    try {
      await onAdd({
        name,
        merchant_pattern: merchantPattern || name.toLowerCase(),
        expected_amount: parseFloat(amount),
        billing_cycle: billingCycle
      })
      onClose()
    } catch (err) {
      console.error('Failed to add subscription:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end justify-center sm:items-center">
      <div className="bg-dark-800 w-full max-w-lg rounded-t-2xl sm:rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="font-semibold text-lg">Add Subscription</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-dark-700 rounded-full transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-dark-400 text-sm mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Netflix, Spotify, etc."
              className="w-full px-4 py-3 bg-dark-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-dark-400 text-sm mb-1">Amount</label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="15.99"
              className="w-full px-4 py-3 bg-dark-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-dark-400 text-sm mb-1">Billing Cycle</label>
            <select
              value={billingCycle}
              onChange={(e) => setBillingCycle(e.target.value)}
              className="w-full px-4 py-3 bg-dark-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="weekly">Weekly</option>
              <option value="biweekly">Biweekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="semiannual">Semiannual (6 months)</option>
              <option value="annual">Annual</option>
            </select>
          </div>

          <div>
            <label className="block text-dark-400 text-sm mb-1">Merchant Pattern (optional)</label>
            <input
              type="text"
              value={merchantPattern}
              onChange={(e) => setMerchantPattern(e.target.value)}
              placeholder="Pattern to match transactions"
              className="w-full px-4 py-3 bg-dark-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <div className="text-dark-500 text-xs mt-1">
              Used to match this subscription in your transactions
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !name || !amount}
            className="w-full py-3 bg-primary-500 hover:bg-primary-600 rounded-xl font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Adding...' : 'Add Subscription'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function Subscriptions() {
  const [loading, setLoading] = useState(true)
  const [subscriptions, setSubscriptions] = useState([])
  const [detected, setDetected] = useState([])
  const [summary, setSummary] = useState({ monthly_total: 0, annual_total: 0, subscription_count: 0, upcoming_week: [], upcoming_month: [] })
  const [showAddModal, setShowAddModal] = useState(false)
  const [detecting, setDetecting] = useState(false)

  // Transaction history modal state
  const [selectedSub, setSelectedSub] = useState(null)
  const [subTransactions, setSubTransactions] = useState([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [subsData, summaryData] = await Promise.all([
        api.getSubscriptions(),
        api.getSubscriptionSummary()
      ])
      setSubscriptions(subsData)
      setSummary(summaryData)
    } catch (err) {
      console.error('Failed to fetch subscriptions:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleDetect = async () => {
    setDetecting(true)
    try {
      const result = await api.detectSubscriptions(90)
      setDetected(result.subscriptions || [])
    } catch (err) {
      console.error('Failed to detect subscriptions:', err)
    } finally {
      setDetecting(false)
    }
  }

  const handleConfirm = async (subscription) => {
    try {
      await api.confirmSubscription({
        name: subscription.merchant,
        merchant_pattern: subscription.merchant_pattern,
        expected_amount: subscription.amount,
        billing_cycle: subscription.billing_cycle
      })
      setDetected(prev => prev.filter(s => s.merchant_pattern !== subscription.merchant_pattern))
      fetchData()
    } catch (err) {
      console.error('Failed to confirm subscription:', err)
    }
  }

  const handleDismiss = async (subscription) => {
    try {
      const created = await api.createSubscription({
        name: subscription.merchant,
        merchant_pattern: subscription.merchant_pattern,
        expected_amount: subscription.amount,
        billing_cycle: subscription.billing_cycle
      })
      await api.deleteSubscription(created.id, true)
      setDetected(prev => prev.filter(s => s.merchant_pattern !== subscription.merchant_pattern))
    } catch (err) {
      console.error('Failed to dismiss subscription:', err)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Remove this subscription?')) return
    try {
      await api.deleteSubscription(id, false)
      fetchData()
    } catch (err) {
      console.error('Failed to delete subscription:', err)
    }
  }

  const handleAdd = async (data) => {
    await api.createSubscription(data)
    fetchData()
  }

  // Handle clicking on a confirmed subscription
  const handleSubClick = async (subscription) => {
    setSelectedSub({ name: subscription.name, id: subscription.id })
    setLoadingTransactions(true)
    setSubTransactions([])

    try {
      const data = await api.getSubscriptionTransactions(subscription.id)
      setSubTransactions(data.transactions || [])
    } catch (err) {
      console.error('Failed to load transactions:', err)
    } finally {
      setLoadingTransactions(false)
    }
  }

  // Handle clicking on a detected subscription
  const handleDetectedClick = async (subscription) => {
    setSelectedSub({ name: subscription.merchant })
    setLoadingTransactions(true)
    setSubTransactions([])

    try {
      const data = await api.getPatternTransactions(subscription.merchant_pattern)
      setSubTransactions(data.transactions || [])
    } catch (err) {
      console.error('Failed to load transactions:', err)
    } finally {
      setLoadingTransactions(false)
    }
  }

  const handleCloseHistory = () => {
    setSelectedSub(null)
    setSubTransactions([])
  }

  useEffect(() => {
    fetchData()
    handleDetect()
  }, [fetchData])

  const confirmedSubs = subscriptions.filter(s => s.is_confirmed)

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton h-8 w-48 mb-4" />
        <div className="skeleton h-24 rounded-2xl mb-4" />
        <div className="skeleton h-16 rounded-xl mb-2" />
        <div className="skeleton h-16 rounded-xl mb-2" />
        <div className="skeleton h-16 rounded-xl" />
      </div>
    )
  }

  return (
    <PullToRefresh onRefresh={fetchData}>
      <div className="p-4">
        <h1 className="text-xl font-bold mb-4">Subscriptions</h1>

        {/* Summary Card */}
        <div className="card mb-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-dark-400 text-sm mb-1">Monthly</div>
              <div className="text-2xl font-bold">
                {formatCurrency(summary.monthly_total)}
              </div>
            </div>
            <div>
              <div className="text-dark-400 text-sm mb-1">Annual</div>
              <div className="text-2xl font-bold">
                {formatCurrency(summary.annual_total)}
              </div>
            </div>
          </div>
          <div className="text-dark-400 text-sm mt-3 pt-3 border-t border-dark-700">
            {summary.subscription_count} active subscription{summary.subscription_count !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Upcoming Charges */}
        {summary.upcoming_week && summary.upcoming_week.length > 0 && (
          <div className="card mb-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">📅</span>
              <div className="font-semibold">Upcoming This Week</div>
            </div>
            <div className="space-y-2">
              {summary.upcoming_week.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center py-2 border-b border-dark-700 last:border-0">
                  <div>
                    <div className="font-medium text-sm">{item.name}</div>
                    <div className="text-dark-400 text-xs">
                      {item.days_until === 0 ? 'Today' : item.days_until === 1 ? 'Tomorrow' : `In ${item.days_until} days`}
                    </div>
                  </div>
                  <div className="font-semibold">{formatCurrency(item.amount)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Confirmed Subscriptions */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold">Your Subscriptions</h2>
            <button
              onClick={() => setShowAddModal(true)}
              className="text-primary-500 text-sm flex items-center gap-1"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add
            </button>
          </div>

          {confirmedSubs.length === 0 ? (
            <div className="card text-center py-6">
              <div className="text-4xl mb-2">🔁</div>
              <div className="text-dark-400">No subscriptions tracked yet</div>
              <div className="text-dark-500 text-sm mt-1">
                Confirm detected ones below or add manually
              </div>
            </div>
          ) : (
            confirmedSubs.map(sub => (
              <SubscriptionCard
                key={sub.id}
                subscription={sub}
                onClick={handleSubClick}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>

        {/* Detected Subscriptions */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-semibold">Detected</h2>
            <button
              onClick={handleDetect}
              disabled={detecting}
              className="text-primary-500 text-sm flex items-center gap-1"
            >
              {detecting ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                  </svg>
                  Scan
                </>
              )}
            </button>
          </div>

          {detected.length === 0 ? (
            <div className="card text-center py-6">
              <div className="text-4xl mb-2">✅</div>
              <div className="text-dark-400">No new subscriptions detected</div>
              <div className="text-dark-500 text-sm mt-1">
                We look for recurring charges with similar amounts
              </div>
            </div>
          ) : (
            detected.map(sub => (
              <DetectedSubscriptionCard
                key={sub.merchant_pattern}
                subscription={sub}
                onClick={handleDetectedClick}
                onConfirm={handleConfirm}
                onDismiss={handleDismiss}
              />
            ))
          )}
        </div>

        {/* Bottom spacer for nav clearance */}
        <div className="h-4" />

        {/* Add Modal */}
        {showAddModal && (
          <AddSubscriptionModal
            onClose={() => setShowAddModal(false)}
            onAdd={handleAdd}
          />
        )}

        {/* Transaction History Modal */}
        {selectedSub && (
          <TransactionHistoryModal
            subscription={selectedSub}
            transactions={subTransactions}
            loading={loadingTransactions}
            onClose={handleCloseHistory}
          />
        )}
      </div>
    </PullToRefresh>
  )
}
