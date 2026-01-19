import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    // Optionally reload the page
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-dark-900">
          <div className="card w-full max-w-md text-center">
            <div className="text-5xl mb-4">😵</div>
            <h1 className="text-xl font-bold mb-2">Something went wrong</h1>
            <p className="text-dark-400 mb-4">
              The app encountered an unexpected error.
            </p>
            {this.state.error && (
              <pre className="text-left text-xs bg-dark-800 p-3 rounded-lg mb-4 overflow-auto max-h-32 text-red-400">
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="w-full py-3 bg-primary-500 hover:bg-primary-600 rounded-xl font-semibold transition-colors"
            >
              Reload App
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
