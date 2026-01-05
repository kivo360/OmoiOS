"use client"

/**
 * Error Boundary Component
 *
 * A reusable error boundary that catches React errors and reports them to Sentry.
 * This provides a better UX by showing a fallback UI instead of a white screen.
 *
 * @example
 * ```tsx
 * <ErrorBoundary fallback={<ErrorFallback />}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 *
 * @example with reset capability
 * ```tsx
 * <ErrorBoundary
 *   fallback={({ error, reset }) => (
 *     <div>
 *       <p>Something went wrong: {error.message}</p>
 *       <button onClick={reset}>Try again</button>
 *     </div>
 *   )}
 * >
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */

import * as Sentry from "@sentry/nextjs"
import { Component, type ReactNode, type ErrorInfo } from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

// ============================================================================
// Types
// ============================================================================

interface FallbackProps {
  error: Error
  errorInfo: ErrorInfo | null
  reset: () => void
}

type FallbackElement = ReactNode | ((props: FallbackProps) => ReactNode)

interface ErrorBoundaryProps {
  children: ReactNode
  /** Custom fallback UI or render function */
  fallback?: FallbackElement
  /** Called when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  /** Custom error category for Sentry filtering */
  category?: string
  /** Additional context to include in error reports */
  context?: Record<string, unknown>
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

// ============================================================================
// Default Fallback Component
// ============================================================================

function DefaultErrorFallback({ error, reset }: FallbackProps) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 p-6 text-center">
      <AlertTriangle className="mb-4 h-10 w-10 text-destructive" />
      <h3 className="mb-2 text-lg font-semibold text-destructive">Something went wrong</h3>
      <p className="mb-4 max-w-md text-sm text-muted-foreground">
        {process.env.NODE_ENV === "development"
          ? error.message
          : "An unexpected error occurred. Our team has been notified."}
      </p>
      <Button variant="outline" size="sm" onClick={reset}>
        <RefreshCw className="mr-2 h-4 w-4" />
        Try again
      </Button>
    </div>
  )
}

// ============================================================================
// Error Boundary Component
// ============================================================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Update state with error info
    this.setState({ errorInfo })

    // Report to Sentry with additional context
    Sentry.withScope((scope) => {
      // Add error category tag for filtering
      if (this.props.category) {
        scope.setTag("error.category", this.props.category)
      }
      scope.setTag("error.boundary", "react")

      // Add component stack
      scope.setExtra("componentStack", errorInfo.componentStack)

      // Add custom context
      if (this.props.context) {
        scope.setContext("errorBoundary", this.props.context)
      }

      // Capture the error
      Sentry.captureException(error)
    })

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo)
  }

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      const fallbackProps: FallbackProps = {
        error: this.state.error,
        errorInfo: this.state.errorInfo,
        reset: this.reset,
      }

      // Use custom fallback if provided
      if (this.props.fallback) {
        if (typeof this.props.fallback === "function") {
          return this.props.fallback(fallbackProps)
        }
        return this.props.fallback
      }

      // Use default fallback
      return <DefaultErrorFallback {...fallbackProps} />
    }

    return this.props.children
  }
}

// ============================================================================
// Functional Wrapper (for use with hooks)
// ============================================================================

/**
 * Higher-order component to wrap a component with an error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">
) {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || "Component"

  const ComponentWithErrorBoundary = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  )

  ComponentWithErrorBoundary.displayName = `withErrorBoundary(${displayName})`

  return ComponentWithErrorBoundary
}

export default ErrorBoundary
