// v2.5 - Mobile/PWA responsive fixes (complete)
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { api, formatCurrency } from '../api'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, ResponsiveContainer, Tooltip, Legend
} from 'recharts'
import PullToRefresh from '../components/PullToRefresh'

const COLORS = ['#1991eb', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#5856d6', '#00c7be', '#ff2d55']

// Hook to detect mobile and PWA (standalone) mode
function useIsMobilePWA() {
  const [isMobilePWA, setIsMobilePWA] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 768
      const standalone = window.matchMedia('(display-mode: standalone)').matches ||
                        window.navigator.standalone === true
      setIsMobile(mobile)
      setIsMobilePWA(mobile && standalone)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  return { isMobile, isMobilePWA }
}

// Popover that positions itself near the click location (or centered on mobile PWA)
function TransactionPopover({ transactions, loading, onClose, title, clickPosition, isMobilePWA }) {
  const popoverRef = useRef(null)
  const [position, setPosition] = useState(null)

  useEffect(() => {
    if (!clickPosition) {
      setPosition(null)
      return
    }

    const isMobile = window.innerWidth <= 768
    const padding = 12

    // Mobile PWA: center the popover for better UX
    if (isMobilePWA || isMobile) {
      const popoverWidth = Math.min(360, window.innerWidth - 32)
      const popoverHeight = Math.min(400, window.innerHeight - 100)
      const top = Math.max(50, (window.innerHeight - popoverHeight) / 2 - 30)
      const left = (window.innerWidth - popoverWidth) / 2

      setPosition({ top, left, width: popoverWidth, height: popoverHeight, centered: true })
      return
    }

    // Desktop: anchor to click position
    const popoverHeight = 480
    const popoverWidth = Math.min(420, window.innerWidth - 24)

    let top = clickPosition.y
    let left = clickPosition.x - (popoverWidth / 2)

    // Keep within horizontal bounds
    if (left < padding) left = padding
    if (left + popoverWidth > window.innerWidth - padding) {
      left = window.innerWidth - popoverWidth - padding
    }

    // Vertically: try to show popover so click point is near the top of the popover
    if (top + popoverHeight > window.innerHeight - padding) {
      top = clickPosition.y - popoverHeight - 10
    }

    // If that puts it off the top, just position at top
    if (top < padding) {
      top = padding
    }

    setPosition({ top, left, width: popoverWidth, centered: false })
  }, [clickPosition, isMobilePWA])

  if (!title || !position) return null

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 9998
        }}
      />
      {/* Popover */}
      <div
        ref={popoverRef}
        style={{
          position: 'fixed',
          top: position.top,
          left: position.left,
          width: position.width,
          maxHeight: position.height || '480px',
          backgroundColor: '#2c2c2e',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 16px',
          borderBottom: '1px solid #3a3a3c',
          flexShrink: 0
        }}>
          <div style={{ fontWeight: 600, color: '#fff', fontSize: '15px' }}>{title}</div>
          <button
            onClick={onClose}
            style={{
              padding: '6px',
              backgroundColor: '#3a3a3c',
              border: 'none',
              borderRadius: '50%',
              cursor: 'pointer',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" style={{ width: '16px', height: '16px' }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Transaction List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px' }}>
              {[1, 2, 3, 4].map(i => (
                <div key={i} style={{ height: '52px', backgroundColor: '#3a3a3c', borderRadius: '10px' }} />
              ))}
            </div>
          ) : transactions.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#8e8e93', padding: '32px 16px', fontSize: '14px' }}>
              No transactions found
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {transactions.slice(0, 35).map(txn => (
                <div
                  key={txn.id}
                  style={{
                    backgroundColor: '#3a3a3c',
                    borderRadius: '10px',
                    padding: '10px 12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, color: '#fff', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {txn.merchant_name || txn.name}
                    </div>
                    <div style={{ color: '#8e8e93', fontSize: '12px', marginTop: '2px' }}>
                      {txn.date ? (() => { const [y,m,d] = txn.date.split('-').map(Number); return new Date(y,m-1,d).toLocaleDateString() })() : 'Pending'}
                    </div>
                  </div>
                  <div style={{ fontWeight: 600, marginLeft: '12px', fontSize: '14px', color: txn.amount > 0 ? '#34c759' : '#fff' }}>
                    {txn.amount > 0 ? '+' : ''}{formatCurrency(txn.amount)}
                  </div>
                </div>
              ))}
              {transactions.length > 35 && (
                <div style={{ textAlign: 'center', color: '#8e8e93', padding: '8px', fontSize: '13px' }}>
                  +{transactions.length - 35} more transactions
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>,
    document.body
  )
}

function NetWorthChart({ data }) {
  if (!data || data.length === 0) return null

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-2">Net Worth Trend</div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis
              dataKey="date"
              tickFormatter={(d) => { const [y,m,day] = d.split('-').map(Number); return new Date(y,m-1,day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
              tick={{ fill: '#8e8e93', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fill: '#8e8e93', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              contentStyle={{ background: '#2c2c2e', border: 'none', borderRadius: '8px' }}
              labelStyle={{ color: '#8e8e93' }}
              formatter={(value) => [formatCurrency(value), '']}
              labelFormatter={(label) => { const [y,m,d] = label.split('-').map(Number); return new Date(y,m-1,d).toLocaleDateString() }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} iconType="line" />
            <Line type="monotone" dataKey="net_worth" name="Net Worth" stroke="#1991eb" strokeWidth={2.5} dot={{ r: 5, fill: '#1991eb' }} />
            <Line type="monotone" dataKey="cash" name="Cash" stroke="#34c759" strokeWidth={2} dot={{ r: 4, fill: '#34c759' }} />
            <Line type="monotone" dataKey="investments" name="Investments" stroke="#ff9500" strokeWidth={2} dot={{ r: 4, fill: '#ff9500' }} />
            <Line type="monotone" dataKey="retirement" name="Retirement" stroke="#af52de" strokeWidth={2} dot={{ r: 4, fill: '#af52de' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function SpendingTrendsChart({ data, onItemClick }) {
  if (!data || data.length === 0) return null

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-4">Monthly Cash Flow</div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="month_name" tickFormatter={(d) => d.split(' ')[0].slice(0, 3)} tick={{ fill: '#8e8e93', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fill: '#8e8e93', fontSize: 10 }} axisLine={false} tickLine={false} width={50} />
            <Tooltip contentStyle={{ background: '#2c2c2e', border: 'none', borderRadius: '8px' }} labelStyle={{ color: '#8e8e93' }} formatter={(value) => [formatCurrency(value), '']} />
            <Bar dataKey="income" name="Income" fill="#34c759" radius={[4, 4, 0, 0]} />
            <Bar dataKey="spending" name="Spending" fill="#ff3b30" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="text-dark-400 text-xs mt-3 mb-2">Tap to see transactions</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.map((monthData) => (
          <div
            key={monthData.month}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 12px',
              backgroundColor: '#2c2c2e',
              borderRadius: '8px'
            }}
          >
            <span style={{ color: '#d1d1d6', fontWeight: 500 }}>{monthData.month_name}</span>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div
                onClick={(e) => onItemClick(e, { type: 'income', month: monthData.month_name, month_start: monthData.month_start, month_end: monthData.month_end })}
                style={{ cursor: 'pointer', padding: '4px 10px', backgroundColor: 'rgba(52, 199, 89, 0.2)', borderRadius: '6px', color: '#34c759', fontWeight: 600, fontSize: '14px' }}
              >
                +{formatCurrency(monthData.income)}
              </div>
              <div
                onClick={(e) => onItemClick(e, { type: 'spending', month: monthData.month_name, month_start: monthData.month_start, month_end: monthData.month_end })}
                style={{ cursor: 'pointer', padding: '4px 10px', backgroundColor: 'rgba(255, 59, 48, 0.2)', borderRadius: '6px', color: '#ff3b30', fontWeight: 600, fontSize: '14px' }}
              >
                -{formatCurrency(monthData.spending)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function SpendingBreakdownChart({ data, onItemClick }) {
  if (!data || !data.by_category || data.by_category.length === 0) return null

  const pieData = data.by_category.slice(0, 8).map((cat, i) => ({
    ...cat, name: cat.display, value: cat.amount, color: COLORS[i % COLORS.length]
  }))

  return (
    <div className="card mb-4">
      <div className="font-semibold mb-4">Spending Breakdown</div>
      <div className="text-dark-400 text-xs mb-2">Tap a category to see transactions</div>
      <div className="flex">
        <div className="w-1/2 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={2} dataKey="value" isAnimationActive={false}>
                {pieData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#2c2c2e', border: 'none', borderRadius: '8px' }} formatter={(value) => [formatCurrency(value), '']} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="w-1/2 space-y-1 overflow-y-auto max-h-40 pr-2">
          {data.by_category.map((cat, i) => (
            <div
              key={cat.category}
              onClick={(e) => onItemClick(e, { type: 'category', category: cat })}
              style={{ cursor: 'pointer', padding: '8px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '14px' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: COLORS[i % COLORS.length], flexShrink: 0 }} />
                <span style={{ color: '#d1d1d6' }}>{cat.display}</span>
              </div>
              <span style={{ fontWeight: 500 }}>{formatCurrency(cat.amount)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function CategoryList({ data, onItemClick, isMobile }) {
  if (!data || !data.by_parent) return null

  const totalSpending = Object.values(data.by_parent).reduce((sum, info) => sum + info.amount, 0)
  const sortedCategories = Object.entries(data.by_parent).sort((a, b) => b[1].amount - a[1].amount)

  // Mobile: single column, smaller fonts. Desktop: two columns
  const gridStyle = isMobile
    ? { display: 'flex', flexDirection: 'column', gap: '12px' }
    : { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }

  const headerFontSize = isMobile ? '18px' : '22px'
  const parentFontSize = isMobile ? '15px' : '18px'
  const itemFontSize = isMobile ? '14px' : '16px'
  const emojiFontSize = isMobile ? '16px' : '18px'

  return (
    <div className="card" style={{ padding: isMobile ? '14px' : '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isMobile ? '14px' : '20px' }}>
        <span style={{ fontWeight: 700, fontSize: headerFontSize }}>By Category</span>
        <span style={{ fontWeight: 700, fontSize: headerFontSize }}>{formatCurrency(totalSpending)}</span>
      </div>
      <div style={gridStyle}>
        {sortedCategories.map(([parent, info]) => (
          <div key={parent} style={{ backgroundColor: '#2c2c2e', borderRadius: '12px', padding: isMobile ? '12px' : '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', borderBottom: '1px solid #3a3a3c', paddingBottom: '10px' }}>
              <span style={{ fontWeight: 700, fontSize: parentFontSize, color: '#fff' }}>{parent}</span>
              <span style={{ fontWeight: 700, fontSize: parentFontSize, color: '#fff' }}>{formatCurrency(info.amount)}</span>
            </div>
            {info.categories.map(cat => (
              <div
                key={cat.category}
                onClick={(e) => onItemClick(e, { type: 'category', category: cat })}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', cursor: 'pointer', fontSize: itemFontSize, color: '#b0b0b5' }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: emojiFontSize }}>{cat.emoji}</span>
                  <span>{cat.display}</span>
                </span>
                <span style={{ fontWeight: 500 }}>{formatCurrency(cat.amount)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function VendorSpendingChart({ data, onItemClick, isMobile }) {
  if (!data || !data.vendors || data.vendors.length === 0) return null

  const maxAmount = Math.max(...data.vendors.map(v => v.amount))
  const headerFontSize = isMobile ? '18px' : '22px'
  const vendorNameWidth = isMobile ? '80px' : '100px'
  const vendorFontSize = isMobile ? '13px' : '14px'

  return (
    <div className="card" style={{ padding: isMobile ? '14px' : '20px', marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isMobile ? '12px' : '16px' }}>
        <span style={{ fontWeight: 700, fontSize: headerFontSize }}>Spend By Vendor</span>
        <span style={{ fontWeight: 700, fontSize: headerFontSize }}>{formatCurrency(data.total)}</span>
      </div>
      <div style={{ fontSize: '12px', color: '#8e8e93', marginBottom: '12px' }}>Tap a vendor to see transactions</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.vendors.map((vendor, i) => (
          <button
            key={vendor.vendor}
            type="button"
            onClick={(e) => onItemClick(e, { type: 'vendor', vendor })}
            style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '8px' : '12px', cursor: 'pointer', padding: '8px', borderRadius: '8px', backgroundColor: '#2c2c2e', border: 'none', width: '100%', textAlign: 'left' }}
          >
            <div style={{ width: vendorNameWidth, flexShrink: 0, fontSize: vendorFontSize, fontWeight: 500, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {vendor.vendor}
            </div>
            <div style={{ flex: 1, height: '24px', backgroundColor: '#1c1c1e', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${(vendor.amount / maxAmount) * 100}%`, height: '100%', backgroundColor: COLORS[i % COLORS.length], borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: '8px', minWidth: isMobile ? '60px' : '70px' }}>
                <span style={{ fontSize: isMobile ? '11px' : '12px', fontWeight: 600, color: '#fff' }}>{formatCurrency(vendor.amount)}</span>
              </div>
            </div>
            <div style={{ width: isMobile ? '38px' : '45px', textAlign: 'right', fontSize: isMobile ? '11px' : '12px', color: '#8e8e93' }}>{vendor.percentage.toFixed(0)}%</div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function Trends() {
  const [loading, setLoading] = useState(true)
  const [netWorthHistory, setNetWorthHistory] = useState([])
  const [spendingTrends, setSpendingTrends] = useState([])
  const [spendingSummary, setSpendingSummary] = useState(null)
  const [vendorSpending, setVendorSpending] = useState(null)
  const [period, setPeriod] = useState('30')

  // Mobile/PWA detection for responsive layout
  const { isMobile, isMobilePWA } = useIsMobilePWA()

  // Popover state
  const [popoverData, setPopoverData] = useState(null) // { title, clickPosition }
  const [popoverTransactions, setPopoverTransactions] = useState([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)
  const [dateRange, setDateRange] = useState({ start: null, end: null })

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setPopoverData(null)
      const days = parseInt(period)

      const endDate = new Date()
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - days)

      const fmtDate = (d) => d.toISOString().split('T')[0]
      const startStr = fmtDate(startDate)
      const endStr = fmtDate(endDate)

      setDateRange({ start: startStr, end: endStr })

      const [nwHistory, trends, summary, vendors] = await Promise.all([
        api.getNetWorthHistory(days),
        api.getSpendingTrendsByDays(days),
        api.getSpendingSummary(startStr, endStr),
        api.getSpendingByVendor(startStr, endStr, 15)
      ])
      setNetWorthHistory(nwHistory)
      setSpendingTrends(trends)
      setSpendingSummary(summary)
      setVendorSpending(vendors)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const closePopover = () => {
    setPopoverData(null)
    setPopoverTransactions([])
  }

  const handleItemClick = async (event, itemData) => {
    // Get actual click coordinates
    const clickX = event.clientX
    const clickY = event.clientY

    let title = ''
    if (itemData.type === 'income') {
      title = `Income - ${itemData.month}`
    } else if (itemData.type === 'spending') {
      title = `Spending - ${itemData.month}`
    } else if (itemData.type === 'category') {
      title = itemData.category.display
    } else if (itemData.type === 'vendor') {
      title = itemData.vendor.vendor
    }

    setPopoverData({ title, clickPosition: { x: clickX, y: clickY } })
    setLoadingTransactions(true)
    setPopoverTransactions([])

    try {
      if (itemData.type === 'income' || itemData.type === 'spending') {
        const params = {
          start_date: itemData.month_start,
          end_date: itemData.month_end,
          limit: 200,
          exclude_transfers: true
        }

        if (itemData.type === 'income') {
          params.amount_min = 0.01
        } else {
          params.amount_max = -0.01
          params.account_type = 'spending'
        }

        const data = await api.getTransactions(params)
        let transactions = data.transactions

        if (itemData.type === 'income') {
          const excludeAccountTypes = ['investment', 'brokerage', 'retirement', 'credit']
          transactions = transactions.filter(txn => !excludeAccountTypes.includes(txn.account_type))
        }

        setPopoverTransactions(transactions)
      } else if (itemData.type === 'category') {
        const data = await api.getTransactions({
          category: itemData.category.category,
          start_date: dateRange.start,
          end_date: dateRange.end,
          limit: 100,
          account_type: 'spending'
        })
        setPopoverTransactions(data.transactions)
      } else if (itemData.type === 'vendor') {
        const data = await api.getTransactions({
          start_date: dateRange.start,
          end_date: dateRange.end,
          limit: 500,
          account_type: 'spending'
        })

        const vendorLower = itemData.vendor.vendor.toLowerCase().trim()
        const vendorFirstWord = vendorLower.split(' ')[0]

        const filtered = (data.transactions || []).filter(txn => {
          const merchantLower = (txn.merchant_name || '').toLowerCase()
          const nameLower = (txn.name || '').toLowerCase()

          if (vendorLower === 'amazon') return merchantLower.includes('amazon') || nameLower.includes('amazon') || nameLower.includes('amzn')
          if (vendorLower === 'doordash') return merchantLower.includes('doordash') || nameLower.includes('doordash') || nameLower.startsWith('dd ')
          if (vendorLower === 'shipt') return merchantLower.includes('shipt') || nameLower.includes('shipt')
          if (vendorLower === 'walmart') return merchantLower.includes('walmart') || nameLower.includes('walmart')
          if (vendorLower === 'target') return merchantLower.includes('target') || nameLower.includes('target')
          if (vendorLower === 'costco') return merchantLower.includes('costco') || nameLower.includes('costco')
          if (vendorLower === 'chevron') return merchantLower.includes('chevron') || nameLower.includes('chevron')

          return merchantLower.includes(vendorLower) || nameLower.includes(vendorLower) ||
                 merchantLower.includes(vendorFirstWord) || nameLower.includes(vendorFirstWord)
        })

        setPopoverTransactions(filtered)
      }
    } catch (err) {
      console.error('Failed to load transactions:', err)
    } finally {
      setLoadingTransactions(false)
    }
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton h-8 w-32 mb-4" />
        <div className="skeleton h-56 rounded-2xl mb-4" />
        <div className="skeleton h-56 rounded-2xl mb-4" />
        <div className="skeleton h-48 rounded-2xl" />
      </div>
    )
  }

  return (
    <>
      <PullToRefresh onRefresh={fetchData}>
        <div className="p-4">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-xl font-bold">Trends</h1>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-3 py-2 bg-dark-700 rounded-lg text-sm focus:outline-none"
            >
              <option value="7">7 Days</option>
              <option value="30">30 Days</option>
              <option value="90">90 Days</option>
              <option value="365">1 Year</option>
            </select>
          </div>

          <NetWorthChart data={netWorthHistory} />
          <SpendingTrendsChart data={spendingTrends} onItemClick={handleItemClick} />

          <Link to="/subscriptions" className="card mb-4 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔁</span>
              <div>
                <div className="font-semibold">Subscriptions</div>
                <div className="text-dark-400 text-sm">Track recurring charges</div>
              </div>
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5 text-dark-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </Link>

          <SpendingBreakdownChart data={spendingSummary} onItemClick={handleItemClick} />
          <CategoryList data={spendingSummary} onItemClick={handleItemClick} isMobile={isMobile} />
          <VendorSpendingChart data={vendorSpending} onItemClick={handleItemClick} isMobile={isMobile} />

          <div className="h-4" />
        </div>
      </PullToRefresh>

      {/* Anchored Popover */}
      <TransactionPopover
        title={popoverData?.title}
        clickPosition={popoverData?.clickPosition}
        transactions={popoverTransactions}
        loading={loadingTransactions}
        onClose={closePopover}
        isMobilePWA={isMobilePWA}
      />
    </>
  )
}
