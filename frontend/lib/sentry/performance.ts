/**
 * Sentry Performance Monitoring Utilities
 *
 * Provides utilities for custom transactions, spans, and Web Vitals tracking.
 */

import * as Sentry from "@sentry/nextjs"

// ============================================================================
// Types
// ============================================================================

export type TransactionName =
  | "onboarding"
  | "checkout"
  | "dashboard-load"
  | "project-creation"
  | "agent-execution"
  | "search"
  | string

interface SpanOptions {
  /** Operation name (e.g., "http.client", "db.query") */
  op: string
  /** Description of the operation */
  description?: string
  /** Additional data to attach to the span */
  data?: Record<string, string | number | boolean | undefined>
}

// ============================================================================
// Custom Transactions
// ============================================================================

/**
 * Start a custom transaction for a user flow
 *
 * @example
 * ```tsx
 * const transaction = startTransaction("onboarding", "User Onboarding Flow")
 *
 * // ... perform onboarding steps ...
 *
 * transaction.finish()
 * ```
 */
export function startTransaction(
  name: TransactionName,
  description?: string,
  op: string = "user.flow"
): Sentry.Span | undefined {
  return Sentry.startInactiveSpan({
    name,
    op,
    attributes: description ? { description } : undefined,
  })
}

/**
 * Measure a specific operation within a transaction
 *
 * @example
 * ```tsx
 * await measureOperation(
 *   { op: "api.fetch", description: "Fetch user profile" },
 *   async () => {
 *     return await fetchUserProfile()
 *   }
 * )
 * ```
 */
export async function measureOperation<T>(
  options: SpanOptions,
  fn: () => Promise<T>
): Promise<T> {
  return Sentry.startSpan(
    {
      name: options.description || options.op,
      op: options.op,
      attributes: options.data,
    },
    async () => {
      return await fn()
    }
  )
}

/**
 * Synchronous version of measureOperation
 */
export function measureOperationSync<T>(options: SpanOptions, fn: () => T): T {
  return Sentry.startSpanManual(
    {
      name: options.description || options.op,
      op: options.op,
      attributes: options.data,
    },
    (span) => {
      try {
        const result = fn()
        span.end()
        return result
      } catch (error) {
        span.setStatus({ code: 2, message: "error" }) // UNSET = 0, OK = 1, ERROR = 2
        span.end()
        throw error
      }
    }
  )
}

// ============================================================================
// User Flow Tracking
// ============================================================================

interface FlowStep {
  name: string
  startedAt: number
}

interface FlowTracker {
  /** Start a new step in the flow */
  startStep: (stepName: string) => void
  /** Complete the current step */
  completeStep: () => void
  /** Complete the entire flow */
  finish: (status?: "ok" | "error" | "cancelled") => void
  /** Add custom data to the flow */
  setData: (key: string, value: unknown) => void
}

const activeFlows = new Map<string, { span: Sentry.Span; currentStep: FlowStep | null; steps: FlowStep[] }>()

/**
 * Track a multi-step user flow (e.g., onboarding, checkout)
 *
 * @example
 * ```tsx
 * const flow = trackUserFlow("onboarding")
 *
 * flow.startStep("select-plan")
 * // ... user selects plan ...
 * flow.completeStep()
 *
 * flow.startStep("enter-payment")
 * // ... user enters payment ...
 * flow.completeStep()
 *
 * flow.finish("ok")
 * ```
 */
export function trackUserFlow(flowName: TransactionName, description?: string): FlowTracker {
  const span = startTransaction(flowName, description)
  const flowId = `${flowName}-${Date.now()}`

  if (span) {
    activeFlows.set(flowId, { span, currentStep: null, steps: [] })
  }

  return {
    startStep(stepName: string) {
      const flow = activeFlows.get(flowId)
      if (!flow) return

      // Complete previous step if any
      if (flow.currentStep) {
        this.completeStep()
      }

      flow.currentStep = {
        name: stepName,
        startedAt: Date.now(),
      }

      // Add breadcrumb for the step
      Sentry.addBreadcrumb({
        category: "user.flow",
        message: `Started step: ${stepName}`,
        level: "info",
        data: { flow: flowName, step: stepName },
      })
    },

    completeStep() {
      const flow = activeFlows.get(flowId)
      if (!flow || !flow.currentStep) return

      const duration = Date.now() - flow.currentStep.startedAt
      flow.steps.push({ ...flow.currentStep })

      // Add step timing data to span
      flow.span.setAttribute(`step.${flow.currentStep.name}.duration_ms`, duration)

      flow.currentStep = null
    },

    finish(status: "ok" | "error" | "cancelled" = "ok") {
      const flow = activeFlows.get(flowId)
      if (!flow) return

      // Complete any pending step
      if (flow.currentStep) {
        this.completeStep()
      }

      // Set final status
      if (status === "ok") {
        flow.span.setStatus({ code: 1 }) // OK
      } else {
        flow.span.setStatus({ code: 2, message: status }) // ERROR
      }

      // Add summary data
      flow.span.setAttribute("steps.count", flow.steps.length)
      flow.span.setAttribute("steps.names", flow.steps.map((s) => s.name).join(","))

      flow.span.end()
      activeFlows.delete(flowId)
    },

    setData(key: string, value: unknown) {
      const flow = activeFlows.get(flowId)
      if (!flow) return

      flow.span.setAttribute(key, value as string | number | boolean)
    },
  }
}

// ============================================================================
// API Performance Tracking
// ============================================================================

/**
 * Create a span for an API call with automatic timing
 */
export async function trackAPICall<T>(
  method: string,
  endpoint: string,
  fn: () => Promise<T>
): Promise<T> {
  return measureOperation(
    {
      op: "http.client",
      description: `${method} ${endpoint}`,
      data: {
        "http.method": method,
        "http.url": endpoint,
      },
    },
    fn
  )
}

// ============================================================================
// Web Vitals
// ============================================================================

interface WebVitalsMetric {
  name: "CLS" | "FCP" | "FID" | "INP" | "LCP" | "TTFB"
  value: number
  rating: "good" | "needs-improvement" | "poor"
}

/**
 * Report a Web Vitals metric to Sentry
 * Note: Sentry automatically captures Web Vitals, but this can be used for custom reporting
 */
export function reportWebVital(metric: WebVitalsMetric): void {
  Sentry.addBreadcrumb({
    category: "web-vitals",
    message: `${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`,
    level: metric.rating === "poor" ? "warning" : "info",
    data: {
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
    },
  })

  // Set as measurement for the current transaction
  Sentry.setMeasurement(metric.name, metric.value, metric.name === "CLS" ? "" : "millisecond")
}

// ============================================================================
// Performance Budgets
// ============================================================================

interface PerformanceBudget {
  /** Maximum allowed value */
  max: number
  /** Unit of measurement */
  unit: "ms" | "bytes" | "count"
}

const DEFAULT_BUDGETS: Record<string, PerformanceBudget> = {
  "page.load": { max: 3000, unit: "ms" },
  "api.call": { max: 500, unit: "ms" },
  "bundle.size": { max: 500000, unit: "bytes" },
  LCP: { max: 2500, unit: "ms" },
  FID: { max: 100, unit: "ms" },
  CLS: { max: 0.1, unit: "count" },
}

/**
 * Check if a metric exceeds its performance budget
 */
export function checkPerformanceBudget(
  metricName: string,
  value: number,
  customBudget?: PerformanceBudget
): { exceeded: boolean; budget: number; actual: number } {
  const budget = customBudget || DEFAULT_BUDGETS[metricName]

  if (!budget) {
    return { exceeded: false, budget: 0, actual: value }
  }

  const exceeded = value > budget.max

  if (exceeded) {
    Sentry.addBreadcrumb({
      category: "performance",
      message: `Performance budget exceeded: ${metricName}`,
      level: "warning",
      data: {
        metric: metricName,
        budget: budget.max,
        actual: value,
        unit: budget.unit,
      },
    })
  }

  return { exceeded, budget: budget.max, actual: value }
}

// ============================================================================
// Hooks for React Components
// ============================================================================

/**
 * Hook to track component render performance
 * Use sparingly - only for components known to have performance issues
 */
export function useRenderTracking(componentName: string): void {
  if (process.env.NODE_ENV === "production") {
    // Only track in production where it matters
    Sentry.addBreadcrumb({
      category: "render",
      message: `Rendered: ${componentName}`,
      level: "debug",
    })
  }
}

/**
 * Create a performance-monitored callback
 */
export function createTrackedCallback<T extends (...args: unknown[]) => unknown>(
  name: string,
  callback: T
): T {
  return ((...args: unknown[]) => {
    const start = performance.now()
    const result = callback(...args)

    // Handle async callbacks
    if (result instanceof Promise) {
      return result.finally(() => {
        const duration = performance.now() - start
        Sentry.addBreadcrumb({
          category: "callback",
          message: `${name} completed`,
          level: "debug",
          data: { duration_ms: duration.toFixed(2) },
        })
      })
    }

    const duration = performance.now() - start
    Sentry.addBreadcrumb({
      category: "callback",
      message: `${name} completed`,
      level: "debug",
      data: { duration_ms: duration.toFixed(2) },
    })

    return result
  }) as T
}
