import { useState, useEffect, useCallback } from 'react'
import { api, formatCurrency, formatPercent } from '../api'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, PieChart, Pie, Cell } from 'recharts'
import PullToRefresh from '../components/PullToRefresh'

function PortfolioCard({ summary, history }) {
  const isPositive = (summary.total_gain_loss || 0) >= 0

  return (
    <div className="card mb-4">
      <div className="text-dark-400 text-sm mb-1">Portfolio Value</div>
      <div className="text-3xl font-bold mb-1">
        {formatCurrency(summary.total_value)}
      </div>

      {summary.total_gain_loss !== null && (
        <div className={`text-sm flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          <span>{isPositive ? '↑' : '↓'}</span>
          <span>{formatCurrency(summary.total_gain_loss, true)}</span>
          {summary.total_gain_loss_pct !== null && (
            <span className="text-dark-500">({formatPercent(summary.total_gain_loss_pct, true)})</span>
          )}
          <span className="text-dark-500 ml-1">all time</span>
        </div>
      )}

      {history && history.length > 1 && (
        <div className="mt-4 h-32 -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={isPositive ? '#34c759' : '#ff3b30'}
                strokeWidth={2}
                dot={false}
              />
              <Tooltip
                contentStyle={{ background: '#2c2c2e', border: 'none', borderRadius: '8px' }}
                labelStyle={{ color: '#8e8e93' }}
                formatter={(value) => [formatCurrency(value), 'Value']}
                labelFormatter={(label) => {
                  const [y, m, d] = label.split('-').map(Number)
                  return new Date(y, m - 1, d).toLocaleDateString()
                }}
              />
              <XAxis dataKey="date" hide />
              <YAxis hide domain={['dataMin - 1000', 'dataMax + 1000']} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-dark-700">
        <div className="text-dark-400 text-xs">
          {summary.holdings_count > 0 ? 'Holdings' : 'Accounts'}
        </div>
        <div className="font-semibold">
          {summary.holdings_count > 0
            ? `${summary.holdings_count} positions`
            : `${summary.accounts_count} accounts`
          }
        </div>
      </div>
    </div>
  )
}

function AccountsBreakdown({ accounts }) {
  if (!accounts || accounts.length === 0) return null

  const typeLabels = {
    investment: 'Investment',
    brokerage: 'Brokerage',
    retirement: 'Retirement'
  }

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-3">By Account</div>
      <div className="space-y-3">
        {accounts.map(acc => {
          const isPositive = (acc.period_change || 0) >= 0
          const hasChange = acc.period_change !== null && acc.period_change !== undefined
          return (
            <div key={acc.account_id} className="flex justify-between items-center py-2 border-b border-dark-700 last:border-0">
              <div>
                <div className="font-medium text-sm">{acc.account_name}</div>
                <div className="text-dark-400 text-xs">
                  {typeLabels[acc.account_type] || acc.account_type}
                  {acc.institution && ` • ${acc.institution}`}
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold">{formatCurrency(acc.value)}</div>
                {hasChange && (
                  <div className={`text-xs flex items-center justify-end gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                    <span>{isPositive ? '▲' : '▼'}</span>
                    <span>{formatPercent(Math.abs(acc.period_change_pct))}</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AllocationChart({ byType, totalValue }) {
  if (!byType || byType.length === 0) return null

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

  const data = byType.map((item, index) => ({
    ...item,
    percentage: totalValue > 0 ? (item.value / totalValue * 100).toFixed(1) : 0,
    color: COLORS[index % COLORS.length]
  }))

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-3">Asset Allocation</div>
      <div className="flex items-center gap-4">
        <div className="w-32 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="type"
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={50}
                paddingAngle={2}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex-1 space-y-2">
          {data.map((item, index) => (
            <div key={item.type} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span>{item.type}</span>
              </div>
              <span className="text-dark-400">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function TopHoldings({ holdings }) {
  if (!holdings || holdings.length === 0) return null

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-3">Top Holdings</div>
      <div className="space-y-3">
        {holdings.map((holding, index) => {
          const isPositive = (holding.gain_loss || 0) >= 0
          return (
            <div key={index} className="flex justify-between items-center py-2 border-b border-dark-700 last:border-0">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">
                  {holding.ticker ? `${holding.ticker}` : holding.security_name}
                </div>
                <div className="text-dark-400 text-xs truncate">
                  {holding.ticker ? holding.security_name : ''}
                  {holding.allocation_pct > 0 && (
                    <span className="ml-1">• {holding.allocation_pct.toFixed(1)}% of portfolio</span>
                  )}
                </div>
              </div>
              <div className="text-right ml-3">
                <div className="font-semibold">{formatCurrency(holding.value)}</div>
                {holding.gain_loss !== null && (
                  <div className={`text-xs ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(holding.gain_loss, true)}
                    {holding.gain_loss_pct !== null && (
                      <span className="ml-1">({formatPercent(holding.gain_loss_pct, true)})</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PeriodSelector({ selected, onChange }) {
  const periods = [
    { value: 30, label: '1M' },
    { value: 90, label: '3M' },
    { value: 180, label: '6M' },
    { value: 365, label: '1Y' }
  ]

  return (
    <div className="flex gap-2 mb-4">
      {periods.map(period => (
        <button
          key={period.value}
          onClick={() => onChange(period.value)}
          className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
            selected === period.value
              ? 'bg-primary-500 text-white'
              : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
          }`}
        >
          {period.label}
        </button>
      ))}
    </div>
  )
}

export default function Investments() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [historyPeriod, setHistoryPeriod] = useState(90)
  const [historyChange, setHistoryChange] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [summaryData, historyData] = await Promise.all([
        api.getInvestmentSummary(historyPeriod),
        api.getInvestmentHistory(historyPeriod)
      ])
      setSummary(summaryData)
      setHistory(historyData.history || [])
      setHistoryChange({
        change: historyData.change,
        change_pct: historyData.change_pct
      })
    } catch (err) {
      console.error('Failed to fetch investment data:', err)
    } finally {
      setLoading(false)
    }
  }, [historyPeriod])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handlePeriodChange = async (days) => {
    setHistoryPeriod(days)
    try {
      const [summaryData, historyData] = await Promise.all([
        api.getInvestmentSummary(days),
        api.getInvestmentHistory(days)
      ])
      setSummary(summaryData)
      setHistory(historyData.history || [])
      setHistoryChange({
        change: historyData.change,
        change_pct: historyData.change_pct
      })
    } catch (err) {
      console.error('Failed to fetch data:', err)
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

  if (!summary || summary.accounts_count === 0) {
    return (
      <div className="p-4">
        <h1 className="text-xl font-bold mb-4">Investments</h1>
        <div className="card text-center py-8">
          <div className="text-4xl mb-3">📈</div>
          <div className="text-dark-400 mb-2">No investment accounts found</div>
          <div className="text-dark-500 text-sm">
            Connect a brokerage or retirement account to track your investments
          </div>
        </div>
      </div>
    )
  }

  return (
    <PullToRefresh onRefresh={fetchData}>
      <div className="p-4">
        <h1 className="text-xl font-bold mb-4">Investments</h1>

        <PeriodSelector selected={historyPeriod} onChange={handlePeriodChange} />

        {historyChange && historyChange.change !== null && (
          <div className="card mb-4 py-3">
            <div className="flex justify-between items-center">
              <span className="text-dark-400 text-sm">
                {historyPeriod === 30 ? '30 Day' : historyPeriod === 90 ? '90 Day' : historyPeriod === 180 ? '6 Month' : '1 Year'} Change
              </span>
              <div className={`font-semibold ${historyChange.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(historyChange.change, true)}
                {historyChange.change_pct !== null && (
                  <span className="ml-1">({formatPercent(historyChange.change_pct, true)})</span>
                )}
              </div>
            </div>
          </div>
        )}

        <PortfolioCard summary={summary} history={history} />

        <AccountsBreakdown accounts={summary.by_account} />

        <AllocationChart byType={summary.by_type} totalValue={summary.total_value} />

        <TopHoldings holdings={summary.top_holdings} />

        <div className="h-4" />
      </div>
    </PullToRefresh>
  )
}
