import { useState, useEffect, createContext, useContext, useCallback } from 'react'

const ToastContext = createContext(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

function ToastItem({ toast, onDismiss }) {
  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => onDismiss(toast.id), toast.duration || 5000)
      return () => clearTimeout(timer)
    }
  }, [toast, onDismiss])

  const bgColor = {
    error: 'bg-red-900/90 border-red-500/50',
    success: 'bg-green-900/90 border-green-500/50',
    warning: 'bg-yellow-900/90 border-yellow-500/50',
    info: 'bg-blue-900/90 border-blue-500/50',
  }[toast.type] || 'bg-dark-800 border-dark-600'

  const iconColor = {
    error: 'text-red-400',
    success: 'text-green-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400',
  }[toast.type] || 'text-dark-300'

  const icon = {
    error: '!',
    success: '✓',
    warning: '!',
    info: 'i',
  }[toast.type] || 'i'

  return (
    <div
      className={`${bgColor} border rounded-xl p-4 shadow-lg flex items-start gap-3 animate-slide-up`}
      role="alert"
    >
      <div className={`${iconColor} w-6 h-6 rounded-full bg-current/20 flex items-center justify-center text-sm font-bold flex-shrink-0`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        {toast.title && (
          <div className="font-semibold text-sm">{toast.title}</div>
        )}
        <div className="text-sm text-dark-200">{toast.message}</div>
        {toast.details && (
          <div className="text-xs text-dark-400 mt-1">{toast.details}</div>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="text-primary-400 text-sm mt-2 hover:underline"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-dark-400 hover:text-white p-1 -mr-1 -mt-1"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { ...toast, id }])
    return id
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const showError = useCallback((message, options = {}) => {
    return addToast({ type: 'error', message, ...options })
  }, [addToast])

  const showSuccess = useCallback((message, options = {}) => {
    return addToast({ type: 'success', message, ...options })
  }, [addToast])

  const showWarning = useCallback((message, options = {}) => {
    return addToast({ type: 'warning', message, ...options })
  }, [addToast])

  const showInfo = useCallback((message, options = {}) => {
    return addToast({ type: 'info', message, ...options })
  }, [addToast])

  // Helper to show API errors nicely
  const showAPIError = useCallback((error) => {
    return addToast({
      type: 'error',
      title: 'Error',
      message: error.message || 'An unexpected error occurred',
      details: error.details,
      duration: error.code === 'NETWORK_ERROR' ? 0 : 5000, // Network errors stay until dismissed
      action: error.code === 'NETWORK_ERROR' ? {
        label: 'Retry',
        onClick: () => window.location.reload()
      } : undefined
    })
  }, [addToast])

  const value = {
    addToast,
    dismissToast,
    showError,
    showSuccess,
    showWarning,
    showInfo,
    showAPIError
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-20 left-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onDismiss={dismissToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
