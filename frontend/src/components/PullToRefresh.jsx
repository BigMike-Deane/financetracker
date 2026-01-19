import { useState, useRef, useCallback } from 'react'

const PULL_THRESHOLD = 80 // pixels to pull before triggering refresh
const MAX_PULL = 120 // maximum pull distance

export default function PullToRefresh({ onRefresh, children }) {
  const [pullDistance, setPullDistance] = useState(0)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const containerRef = useRef(null)
  const startY = useRef(0)
  const isPulling = useRef(false)

  const handleTouchStart = useCallback((e) => {
    // Only enable pull-to-refresh when scrolled to top
    if (containerRef.current?.scrollTop === 0) {
      startY.current = e.touches[0].clientY
      isPulling.current = true
    }
  }, [])

  const handleTouchMove = useCallback((e) => {
    if (!isPulling.current || isRefreshing) return

    const currentY = e.touches[0].clientY
    const diff = currentY - startY.current

    if (diff > 0 && containerRef.current?.scrollTop === 0) {
      // Apply resistance to make pull feel natural
      const distance = Math.min(diff * 0.5, MAX_PULL)
      setPullDistance(distance)

      // Prevent default scroll when pulling
      if (distance > 10) {
        e.preventDefault()
      }
    }
  }, [isRefreshing])

  const handleTouchEnd = useCallback(async () => {
    if (!isPulling.current) return
    isPulling.current = false

    if (pullDistance >= PULL_THRESHOLD && !isRefreshing) {
      setIsRefreshing(true)
      setPullDistance(PULL_THRESHOLD) // Hold at threshold during refresh

      try {
        await onRefresh()
      } catch (err) {
        console.error('Refresh failed:', err)
      } finally {
        setIsRefreshing(false)
        setPullDistance(0)
      }
    } else {
      setPullDistance(0)
    }
  }, [pullDistance, isRefreshing, onRefresh])

  const progress = Math.min(pullDistance / PULL_THRESHOLD, 1)
  const showIndicator = pullDistance > 10 || isRefreshing

  return (
    <div
      ref={containerRef}
      className="pull-to-refresh-container"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{
        height: '100%',
        overflow: 'auto',
        WebkitOverflowScrolling: 'touch'
      }}
    >
      {/* Pull indicator */}
      <div
        className="pull-indicator"
        style={{
          height: showIndicator ? `${pullDistance}px` : '0px',
          opacity: showIndicator ? 1 : 0,
          transition: isPulling.current ? 'none' : 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden'
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          {isRefreshing ? (
            <div className="refresh-spinner" />
          ) : (
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: `rotate(${progress * 180}deg)`,
                opacity: 0.7,
                transition: isPulling.current ? 'none' : 'transform 0.2s ease'
              }}
            >
              <path d="M12 5v14M19 12l-7 7-7-7" />
            </svg>
          )}
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {isRefreshing
              ? 'Refreshing...'
              : progress >= 1
                ? 'Release to refresh'
                : 'Pull to refresh'}
          </span>
        </div>
      </div>

      {/* Content */}
      <div
        style={{
          transform: `translateY(${isRefreshing ? 0 : 0}px)`,
          transition: isPulling.current ? 'none' : 'transform 0.2s ease'
        }}
      >
        {children}
      </div>

      <style>{`
        .refresh-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid var(--text-secondary);
          border-top-color: var(--primary);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .pull-indicator {
          background: linear-gradient(180deg, var(--bg-dark) 0%, transparent 100%);
        }
      `}</style>
    </div>
  )
}
