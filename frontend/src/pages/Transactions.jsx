import { useState, useEffect } from 'react'
import { api, formatCurrency, formatDate } from '../api'
import PullToRefresh from '../components/PullToRefresh'

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
              <div className="text-dark-400 text-xs">
                {group.transactions.length} similar transactions
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
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${txn.amount > 0 ? 'text-green-400' : ''}`}>
                      {formatCurrency(txn.amount)}
                    </span>
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
        include_pending: includePending
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

  useEffect(() => {
    fetchTransactions(true)
  }, [search, activeTab, includePending])

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

          {/* Results count and pending toggle */}
          <div className="flex justify-between items-center text-sm mb-4">
            <div className="text-dark-400">
              {total} {activeTab === 'spending' ? 'transactions' : 'investment transactions'}
            </div>
            <button
              onClick={() => setIncludePending(!includePending)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                includePending
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                  : 'bg-dark-700 text-dark-400 hover:bg-dark-600'
              }`}
            >
              {includePending ? '⏳ Showing Pending' : 'Show Pending'}
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
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {activeTab === 'investment' ? '📊' : txn.category_emoji}
                      </span>
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          {txn.merchant_name || txn.name}
                          {txn.is_pending && (
                            <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">
                              Pending
                            </span>
                          )}
                        </div>
                        <div className="text-dark-400 text-xs">
                          {activeTab === 'investment'
                            ? txn.account_name
                            : `${txn.category_display} • ${txn.account_name}`
                          }
                        </div>
                      </div>
                    </div>
                    <div className={`font-semibold ${txn.amount > 0 ? 'text-green-400' : ''}`}>
                      {txn.amount > 0 ? '+' : ''}{formatCurrency(txn.amount)}
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
  )
}
