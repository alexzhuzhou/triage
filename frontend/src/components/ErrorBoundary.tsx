import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-lg p-8 max-w-lg w-full border-2 border-red-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-xl">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">
                Something went wrong
              </h1>
            </div>

            <p className="text-gray-600 mb-6">
              An unexpected error occurred. Please refresh the page and try again.
              If the problem persists, contact support.
            </p>

            {this.state.error && (
              <details className="mb-6">
                <summary className="cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
                  Error details
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs overflow-auto">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}

            <button
              onClick={() => window.location.reload()}
              className="w-full px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-all shadow-md font-semibold flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
