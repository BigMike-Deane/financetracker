import { useState, useEffect } from 'react'
import { api, formatCurrency, formatDate } from '../api'
import PullToRefresh from '../components/PullToRefresh'

function SplitModal({ transaction, categories, onClose, onSplit }) {
  const [splits, setSplits] = useState([
    { amount: Math.abs(transaction.amount) / 2, category: transaction.category || 'uncategorized', notes: '' },
    { amount: Math.abs(transaction.amount) / 2, category: 'uncategorized', notes: '' }
  ])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isExpense = transaction.amount < 0
  const originalAmount = Math.abs(transaction.amount)
  const totalSplit = splits.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0)
  const remaining = originalAmount - totalSplit
  const isValid = Math.abs(remaining) < 0.01 && splits.length >= 2

  const handleSplitChange = (index, field, value) => {
    const newSplits = [...splits]
    newSplits[index] = { ...newSplits[index], [field]: value }
    setSplits(newSplits)
  }

  const addSplit = () => {
    setSplits([...splits, { amount: 0, category: 'uncategorized', notes: '' }])
  }

  const removeSplit = (index) => {
    if (splits.length > 2) {
      setSplits(splits.filter((_, i) => i !== index))
    }
  }

  const handleSubmit = async () => {
    if (!isValid) return

    setLoading(true)
    setError(null)

    try {
      // Convert amounts back to negative if expense
      const splitData = splits.map(s => ({
        amount: isExpense ? -parseFloat(s.amount) : parseFloat(s.amount),
        category: s.category,
        notes: s.notes || null
      }))

      await api.splitTransaction(transaction.id, splitData)
      onSplit()
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to split transaction')
    } finally {
      setLoading(false)
    }
  }

  // Group categories by parent
  const groupedCategories = categories.reduce((acc, cat) => {
    if (!acc[cat.parent]) acc[cat.parent] = []
    acc[cat.parent].push(cat)
    return acc
  }, {})

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-800 rounded-2xl p-4 max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Split Transaction</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Original transaction info */}
        <div className="bg-dark-700 rounded-xl p-3 mb-4">
          <div className="font-medium">{transaction.merchant_name || transaction.name}</div>
          <div className="text-dark-400 text-sm">{transaction.date} • {transaction.account_name}</div>
          <div className={`text-lg font-bold mt-1 ${isExpense ? '' : 'text-green-400'}`}>
            {formatCurrency(transaction.amount)}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Splits */}
        <div className="space-y-3 mb-4">
          {splits.map((split, index) => (
            <div key={index} className="bg-dark-700 rounded-xl p-3">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">Split {index + 1}</span>
                {splits.length > 2 && (
                  <button
                    onClick={() => removeSplit(index)}
                    className="text-red-400 hover:text-red-300 text-xs"
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label className="text-dark-400 text-xs block mb-1">Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={split.amount}
                    onChange={(e) => handleSplitChange(index, 'amount', e.target.value)}
                    className="w-full px-3 py-2 bg-dark-600 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="text-dark-400 text-xs block mb-1">Category</label>
                  <select
                    value={split.category}
                    onChange={(e) => handleSplitChange(index, 'category', e.target.value)}
                    className="w-full px-3 py-2 bg-dark-600 rounded-lg text-sm focus:outline-none"
                  >
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
              </div>

              <input
                type="text"
                placeholder="Notes (optional)"
                value={split.notes}
                onChange={(e) => handleSplitChange(index, 'notes', e.target.value)}
                className="w-full px-3 py-2 bg-dark-600 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          ))}
        </div>

        {/* Add split button */}
        <button
          onClick={addSplit}
          className="w-full py-2 mb-4 border border-dashed border-dark-600 rounded-xl text-dark-400 text-sm hover:border-primary-500 hover:text-primary-400 transition-colors"
        >
          + Add Another Split
        </button>

        {/* Summary */}
        <div className="bg-dark-700 rounded-xl p-3 mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-dark-400">Original</span>
            <span>{formatCurrency(originalAmount)}</span>
          </div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-dark-400">Split total</span>
            <span>{formatCurrency(totalSplit)}</span>
          </div>
          <div className={`flex justify-between text-sm font-medium ${
            Math.abs(remaining) < 0.01 ? 'text-green-400' : 'text-red-400'
          }`}>
            <span>Remaining</span>
            <span>{formatCurrency(remaining)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-3 bg-dark-700 rounded-xl font-medium hover:bg-dark-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValid || loading}
            className="flex-1 py-3 bg-primary-500 rounded-xl font-medium hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {loading ? 'Splitting...' : 'Split Transaction'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DuplicatesView() {
  const [loading, setLoading] = useState(true)
  const [duplicates, setDuplicates] = useState(null)
  const [processingId, setProcessingId] = useState(null)

  const fetchDuplicates = async () => {
    try {
      setLoading(true)
      const data = await api.getDuplicates(90)
      setDuplicates(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDuplicates()
  }, [])

  const handleExclude = async (id) => {
    setProcessingId(id)
    try {
      await api.excludeTransaction(id)
      await fetchDuplicates()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessingId(null)
    }
  }

  const handleInclude = async (id) => {
    setProcessingId(id)
    try {
      await api.includeTransaction(id)
      await fetchDuplicates()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessingId(null)
    }
  }

  const handleMarkNotDuplicate = async (id) => {
    setProcessingId(id)
    try {
      await api.markNotDuplicate(id)
      await fetchDuplicates()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessingId(null)
    }
  }

  const handleDismissGroup = async (group) => {
    setProcessingId(`group-${group.amount}`)
    try {
      // Mark all transactions in group as not duplicates
      for (const txn of group.transactions) {
        await api.markNotDuplicate(txn.id)
      }
      await fetchDuplicates()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessingId(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-24 rounded-xl" />
        <div className="skeleton h-24 rounded-xl" />
        <div className="skeleton h-24 rounded-xl" />
      </div>
    )
  }

  if (!duplicates || duplicates.count === 0) {
    return (
      <div className="card text-center py-8">
        <div className="text-4xl mb-4">✅</div>
        <div className="text-lg font-semibold mb-2">No Duplicates Found</div>
        <div className="text-dark-400 text-sm">
          We scanned the last 90 days and found no potential duplicate transactions.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="card mb-4 bg-yellow-500/10 border border-yellow-500/30">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <div className="font-medium text-yellow-400">
              {duplicates.count} potential duplicate {duplicates.count === 1 ? 'group' : 'groups'} found
            </div>
            <div className="text-dark-400 text-sm">
              Review these transactions and exclude duplicates from your reports.
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {duplicates.groups.map((group, idx) => (
          <div key={idx} className="card">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-dark-700">
              <div className="font-semibold text-primary-400">
                {formatCurrency(group.amount)} transactions
              </div>
              <div className="flex items-center gap-2">
                <span className="text-dark-400 text-xs">
                  {group.transactions.length} similar
                </span>
                <button
                  onClick={() => handleDismissGroup(group)}
                  disabled={processingId === `group-${group.amount}`}
                  className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50"
                  title="Mark all as not duplicates"
                >
                  {processingId === `group-${group.amount}` ? 'Dismissing...' : 'Dismiss Group'}
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {group.transactions.map(txn => (
                <div
                  key={txn.id}
                  className={`flex justify-between items-start p-3 rounded-lg ${
                    txn.is_excluded ? 'bg-dark-700/50 opacity-60' : 'bg-dark-800'
                  }`}
                >
                  <div className="flex-1">
                    <div className="font-medium text-sm flex items-center gap-2">
                      {txn.merchant_name || txn.name}
                      {txn.is_excluded && (
                        <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">
                          Excluded
                        </span>
                      )}
                    </div>
                    <div className="text-dark-400 text-xs mt-1">
                      {txn.date} • {txn.account_name}
                    </div>
                    <div className="text-dark-500 text-xs">
                      {txn.category_display}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`font-semibold ${txn.amount > 0 ? 'text-green-400' : ''}`}>
                      {formatCurrency(txn.amount)}
                    </span>
                    <button
                      onClick={() => handleMarkNotDuplicate(txn.id)}
                      disabled={processingId === txn.id}
                      className="p-1.5 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50"
                      title="Not a duplicate - keep counting"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    </button>
                    {txn.is_excluded ? (
                      <button
                        onClick={() => handleInclude(txn.id)}
                        disabled={processingId === txn.id}
                        className="p-1.5 rounded bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:opacity-50"
                        title="Include in reports"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleExclude(txn.id)}
                        disabled={processingId === txn.id}
                        className="p-1.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50"
                        title="Exclude from reports (mark as duplicate)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Transactions() {
  const [loading, setLoading] = useState(true)
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [activeTab, setActiveTab] = useState('spending') // 'spending', 'investment', or 'duplicates'
  const [includePending, setIncludePending] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const [categories, setCategories] = useState([])
  const [splitTransaction, setSplitTransaction] = useState(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const limit = 50

  const fetchTransactions = async (reset = false) => {
    try {
      if (reset) setLoading(true)
      const newOffset = reset ? 0 : offset
      const data = await api.getTransactions({
        limit,
        offset: newOffset,
        search: search || undefined,
        account_type: activeTab, // Filter by spending or investment
        include_pending: includePending,
        start_date: startDate || undefined,
        end_date: endDate || undefined
      })
      setTransactions(reset ? data.transactions : [...transactions, ...data.transactions])
      setTotal(data.total)
      setOffset(newOffset + limit)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Fetch pending count for badge
  const fetchPendingCount = async () => {
    try {
      const data = await api.getTransactions({
        limit: 1,
        account_type: activeTab,
        include_pending: true
      })
      const dataWithoutPending = await api.getTransactions({
        limit: 1,
        account_type: activeTab,
        include_pending: false
      })
      setPendingCount(data.total - dataWithoutPending.total)
    } catch (err) {
      console.error(err)
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

  useEffect(() => {
    fetchCategories()
  }, [])

  useEffect(() => {
    fetchTransactions(true)
  }, [search, activeTab, includePending, startDate, endDate])

  useEffect(() => {
    if (activeTab !== 'duplicates') {
      fetchPendingCount()
    }
  }, [activeTab])

  const handleSearch = (e) => {
    setSearch(e.target.value)
    setOffset(0)
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setSearch('')
    setOffset(0)
    setTransactions([])
  }

  const groupByDate = (txns) => {
    const groups = {}
    txns.forEach(txn => {
      const date = txn.date
      if (!groups[date]) groups[date] = []
      groups[date].push(txn)
    })
    return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
  }

  const grouped = groupByDate(transactions)

  if (loading && transactions.length === 0) {
    return (
      <div className="p-4">
        <div className="skeleton h-10 rounded-xl mb-4" />
        <div className="skeleton h-12 rounded-xl mb-4" />
        <div className="skeleton h-16 rounded-xl mb-2" />
        <div className="skeleton h-16 rounded-xl mb-2" />
        <div className="skeleton h-16 rounded-xl mb-2" />
        <div className="skeleton h-16 rounded-xl" />
      </div>
    )
  }

  const handleRefresh = async () => {
    await fetchTransactions(true)
  }

  return (
    <>
      {/* Split Modal */}
      {splitTransaction && (
        <SplitModal
          transaction={splitTransaction}
          categories={categories}
          onClose={() => setSplitTransaction(null)}
          onSplit={() => fetchTransactions(true)}
        />
      )}

      <PullToRefresh onRefresh={handleRefresh}>
        <div className="p-4">
          <h1 className="text-xl font-bold mb-4">Activity</h1>

        {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => handleTabChange('spending')}
          className={`flex-1 py-2.5 px-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-1.5 text-sm ${
            activeTab === 'spending'
              ? 'bg-primary-500 text-white'
              : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
          }`}
        >
          <span>💳</span>
          <span>Spending</span>
        </button>
        <button
          onClick={() => handleTabChange('investment')}
          className={`flex-1 py-2.5 px-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-1.5 text-sm ${
            activeTab === 'investment'
              ? 'bg-primary-500 text-white'
              : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
          }`}
        >
          <span>📈</span>
          <span>Invest</span>
        </button>
        <button
          onClick={() => handleTabChange('duplicates')}
          className={`flex-1 py-2.5 px-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-1.5 text-sm ${
            activeTab === 'duplicates'
              ? 'bg-yellow-500 text-white'
              : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
          }`}
        >
          <span>🔍</span>
          <span>Duplicates</span>
        </button>
      </div>

      {/* Duplicates View */}
      {activeTab === 'duplicates' ? (
        <DuplicatesView />
      ) : (
        <>
          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              placeholder={activeTab === 'spending' ? 'Search spending...' : 'Search investments...'}
              value={search}
              onChange={handleSearch}
              className="w-full px-4 py-3 bg-dark-800 rounded-xl text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Date Range Filter */}
          <div className="flex gap-2 mb-4">
            <div className="flex-1">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="From"
              />
            </div>
            <div className="flex-1">
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="To"
              />
            </div>
            {(startDate || endDate) && (
              <button
                onClick={() => { setStartDate(''); setEndDate(''); }}
                className="px-3 py-2 bg-dark-700 rounded-xl text-dark-400 hover:bg-dark-600 text-sm"
                title="Clear dates"
              >
                ✕
              </button>
            )}
          </div>

          {/* Results count and pending toggle */}
          <div className="flex justify-between items-center text-sm mb-4">
            <div className="text-dark-400">
              {total} {activeTab === 'spending' ? 'transactions' : 'investment transactions'}
            </div>
            <button
              onClick={() => setIncludePending(!includePending)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                includePending
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  : 'bg-dark-700 text-dark-400 hover:bg-dark-600'
              }`}
            >
              {includePending ? '⏳ Showing Pending' : 'Show Pending'}
              {pendingCount > 0 && !includePending && (
                <span className="bg-yellow-500 text-black text-xs px-1.5 py-0.5 rounded-full font-bold">
                  {pendingCount}
                </span>
              )}
            </button>
          </div>

          {/* Transactions by date */}
          {grouped.map(([date, txns]) => (
            <div key={date} className="mb-4">
              <div className="text-dark-400 text-sm mb-2 sticky top-0 bg-dark-950 py-2">
                {(() => {
                  const [y, m, d] = date.split('-').map(Number)
                  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric'
                  })
                })()}
              </div>

              <div className="space-y-2">
                {txns.map(txn => (
                  <div
                    key={txn.id}
                    className={`card flex justify-between items-center py-3 ${txn.is_pending ? 'border border-yellow-500/30 bg-yellow-500/5' : ''}`}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className="text-2xl">
                        {activeTab === 'investment' ? '📊' : txn.category_emoji}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium flex items-center gap-2">
                          <span className="truncate">{txn.merchant_name || txn.name}</span>
                          {txn.is_pending && (
                            <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded flex-shrink-0">
                              Pending
                            </span>
                          )}
                        </div>
                        <div className="text-dark-400 text-xs truncate">
                          {activeTab === 'investment'
                            ? txn.account_name
                            : `${txn.category_display} • ${txn.account_name}`
                          }
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className={`font-semibold ${txn.amount > 0 ? 'text-green-400' : ''}`}>
                        {txn.amount > 0 ? '+' : ''}{formatCurrency(txn.amount)}
                      </div>
                      {activeTab === 'spending' && !txn.is_pending && (
                        <button
                          onClick={() => setSplitTransaction(txn)}
                          className="p-1.5 text-dark-400 hover:text-primary-400 hover:bg-dark-700 rounded transition-colors"
                          title="Split transaction"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Load more */}
          {transactions.length < total && (
            <button
              onClick={() => fetchTransactions(false)}
              disabled={loading}
              className="w-full py-3 bg-dark-700 rounded-xl font-medium hover:bg-dark-600 transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Load More'}
            </button>
          )}

          {transactions.length === 0 && !loading && (
            <div className="card text-center py-8">
              <div className="text-4xl mb-4">
                {activeTab === 'spending' ? '💳' : '📈'}
              </div>
              <div className="text-lg font-semibold mb-2">
                {activeTab === 'spending' ? 'No spending transactions' : 'No investment activity'}
              </div>
              <div className="text-dark-400 text-sm">
                {search
                  ? 'Try a different search term'
                  : activeTab === 'spending'
                    ? 'Transactions from your checking, savings, and credit cards will appear here'
                    : 'Transactions from your brokerage and retirement accounts will appear here'
                }
              </div>
            </div>
          )}
        </>
      )}

          {/* Bottom spacer for nav clearance */}
          <div className="h-4" />
        </div>
      </PullToRefresh>
    </>
  )
}
