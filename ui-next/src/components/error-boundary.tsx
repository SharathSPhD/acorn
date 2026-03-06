"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 m-4">
            <h2 className="text-sm font-semibold text-red-800 mb-2">
              Something went wrong
            </h2>
            <pre className="text-xs text-red-600 whitespace-pre-wrap break-words max-h-40 overflow-auto">
              {this.state.error?.message}
              {"\n"}
              {this.state.error?.stack}
            </pre>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-3 text-xs text-red-700 underline hover:text-red-900"
            >
              Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
