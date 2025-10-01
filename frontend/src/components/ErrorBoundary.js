import React from 'react';

/**
 * Generic React error boundary to prevent the entire app from going blank (white page)
 * when an uncaught rendering error occurs. Displays a minimal fallback UI and
 * logs the error details to the console for diagnostics.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] Uncaught render error:', error, info);
    this.setState({ info });
  }

  handleReload = () => {
    // Clear potential problematic transient auth state while keeping tokens
    this.setState({ hasError: false, error: null, info: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gray-50 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-2">Something went wrong</h1>
          <p className="text-gray-600 mb-4">An unexpected error occurred and was caught. A reload usually fixes this.</p>
          {this.state.error && (
            <pre className="text-xs bg-gray-100 p-3 rounded max-w-xl overflow-x-auto text-left mb-4">
              {String(this.state.error.message || this.state.error)}
            </pre>
          )}
          <button
            onClick={this.handleReload}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
