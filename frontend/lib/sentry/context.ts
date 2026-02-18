/**
 * Sentry Context Management
 *
 * Provides utilities for adding rich context to Sentry errors,
 * including user information, request details, and breadcrumbs.
 */

import * as Sentry from "@sentry/nextjs";
import type { User } from "@/lib/api/types";

// ============================================================================
// Error Categories
// ============================================================================

export type ErrorCategory =
  | "api"
  | "validation"
  | "auth"
  | "network"
  | "render"
  | "user";

export type ErrorSeverity = "fatal" | "error" | "warning" | "info";

// ============================================================================
// User Context
// ============================================================================

/**
 * Hash email for privacy while maintaining uniqueness
 * Uses a simple hash for client-side (Sentry will group by this)
 */
function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16);
}

/**
 * Set user context when user logs in
 * This associates all subsequent errors with the user
 */
export function setUserContext(user: User | null): void {
  if (!user) {
    Sentry.setUser(null);
    return;
  }

  Sentry.setUser({
    id: user.id,
    username: user.full_name || undefined,
    // Hash email for privacy while maintaining groupability
    email: user.email ? `${hashString(user.email)}@hashed` : undefined,
  });

  // Set additional user tags
  Sentry.setTag("user.role", user.is_super_admin ? "admin" : "user");
  Sentry.setTag("user.verified", String(user.is_verified));
  Sentry.setTag("user.waitlist", user.waitlist_status || "none");
}

/**
 * Clear user context on logout
 */
export function clearUserContext(): void {
  Sentry.setUser(null);
  Sentry.setTag("user.role", undefined);
  Sentry.setTag("user.verified", undefined);
  Sentry.setTag("user.waitlist", undefined);
}

// ============================================================================
// Breadcrumbs
// ============================================================================

interface APIBreadcrumbData {
  method: string;
  url: string;
  status?: number;
  duration?: number;
  error?: string;
}

/**
 * Add breadcrumb for API requests
 */
export function addAPIBreadcrumb(data: APIBreadcrumbData): void {
  const { method, url, status, duration, error } = data;

  // Determine level based on status/error
  let level: Sentry.SeverityLevel = "info";
  if (error || (status && status >= 500)) {
    level = "error";
  } else if (status && status >= 400) {
    level = "warning";
  }

  // Remove sensitive query params from URL
  const sanitizedUrl = sanitizeUrl(url);

  Sentry.addBreadcrumb({
    category: "api",
    message: `${method} ${sanitizedUrl}`,
    level,
    data: {
      status,
      duration: duration ? `${duration}ms` : undefined,
      error,
    },
  });
}

/**
 * Add breadcrumb for navigation events
 */
export function addNavigationBreadcrumb(from: string, to: string): void {
  Sentry.addBreadcrumb({
    category: "navigation",
    message: `Navigated to ${sanitizeUrl(to)}`,
    level: "info",
    data: {
      from: sanitizeUrl(from),
      to: sanitizeUrl(to),
    },
  });
}

/**
 * Add breadcrumb for user actions (clicks, form submissions)
 */
export function addUserActionBreadcrumb(
  action: string,
  target?: string,
  data?: Record<string, unknown>,
): void {
  Sentry.addBreadcrumb({
    category: "user",
    message: target ? `${action}: ${target}` : action,
    level: "info",
    data,
  });
}

/**
 * Add breadcrumb for state changes
 */
export function addStateBreadcrumb(
  message: string,
  data?: Record<string, unknown>,
): void {
  Sentry.addBreadcrumb({
    category: "state",
    message,
    level: "info",
    data,
  });
}

// ============================================================================
// Error Capturing with Context
// ============================================================================

interface CaptureErrorOptions {
  /** Error category for filtering */
  category?: ErrorCategory;
  /** Error severity */
  severity?: ErrorSeverity;
  /** Additional tags */
  tags?: Record<string, string>;
  /** Additional context data */
  extra?: Record<string, unknown>;
  /** User affected (if different from global context) */
  user?: { id: string; email?: string };
}

/**
 * Capture an error with rich context
 */
export function captureError(
  error: Error,
  options: CaptureErrorOptions = {},
): string {
  const { category, severity = "error", tags = {}, extra = {}, user } = options;

  return Sentry.withScope((scope) => {
    // Set error category
    if (category) {
      scope.setTag("error.category", category);
    }

    // Set severity
    scope.setTag("error.severity", severity);
    scope.setLevel(severity as Sentry.SeverityLevel);

    // Set custom tags
    Object.entries(tags).forEach(([key, value]) => {
      scope.setTag(key, value);
    });

    // Set extra context
    Object.entries(extra).forEach(([key, value]) => {
      scope.setExtra(key, value);
    });

    // Override user if provided
    if (user) {
      scope.setUser({
        id: user.id,
        email: user.email ? `${hashString(user.email)}@hashed` : undefined,
      });
    }

    return Sentry.captureException(error);
  });
}

/**
 * Capture an API error with request context
 */
export function captureAPIError(
  error: Error,
  request: {
    method: string;
    url: string;
    status?: number;
    body?: unknown;
  },
  options: Omit<CaptureErrorOptions, "category"> = {},
): string {
  return captureError(error, {
    ...options,
    category: "api",
    extra: {
      ...options.extra,
      request: {
        method: request.method,
        url: sanitizeUrl(request.url),
        status: request.status,
        // Don't include request body - may contain sensitive data
      },
    },
    tags: {
      ...options.tags,
      "api.method": request.method,
      "api.status": String(request.status || "unknown"),
    },
  });
}

/**
 * Capture a validation error with form context
 */
export function captureValidationError(
  error: Error,
  formId: string,
  fields?: string[],
  options: Omit<CaptureErrorOptions, "category"> = {},
): string {
  return captureError(error, {
    ...options,
    category: "validation",
    severity: "warning",
    extra: {
      ...options.extra,
      form: formId,
      fields,
    },
    tags: {
      ...options.tags,
      "form.id": formId,
    },
  });
}

/**
 * Capture an authentication error
 */
export function captureAuthError(
  error: Error,
  action: "login" | "logout" | "refresh" | "register" | "verify",
  options: Omit<CaptureErrorOptions, "category"> = {},
): string {
  return captureError(error, {
    ...options,
    category: "auth",
    severity: action === "logout" ? "warning" : "error",
    tags: {
      ...options.tags,
      "auth.action": action,
    },
  });
}

// ============================================================================
// Scoped Context
// ============================================================================

/**
 * Run a function with additional Sentry context
 * Useful for adding context to a specific operation
 */
export async function withSentryContext<T>(
  context: {
    operation: string;
    tags?: Record<string, string>;
    extra?: Record<string, unknown>;
  },
  fn: () => Promise<T>,
): Promise<T> {
  return Sentry.withScope(async (scope) => {
    scope.setTransactionName(context.operation);

    if (context.tags) {
      Object.entries(context.tags).forEach(([key, value]) => {
        scope.setTag(key, value);
      });
    }

    if (context.extra) {
      Object.entries(context.extra).forEach(([key, value]) => {
        scope.setExtra(key, value);
      });
    }

    try {
      return await fn();
    } catch (error) {
      if (error instanceof Error) {
        Sentry.captureException(error);
      }
      throw error;
    }
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Remove sensitive data from URLs
 */
function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url, "http://localhost");

    // Remove sensitive query parameters
    const sensitiveParams = [
      "token",
      "api_key",
      "password",
      "secret",
      "key",
      "auth",
    ];
    sensitiveParams.forEach((param) => {
      if (parsed.searchParams.has(param)) {
        parsed.searchParams.set(param, "[REDACTED]");
      }
    });

    // Return just path + sanitized query for relative URLs
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    // If URL parsing fails, return as-is but remove obvious tokens
    return url.replace(/token=[^&]+/g, "token=[REDACTED]");
  }
}

/**
 * Create a scoped error reporter for a specific feature
 */
export function createScopedErrorReporter(feature: string) {
  return {
    captureError: (
      error: Error,
      options: Omit<CaptureErrorOptions, "tags"> = {},
    ) =>
      captureError(error, {
        ...options,
        tags: { feature },
      }),

    addBreadcrumb: (message: string, data?: Record<string, unknown>) =>
      Sentry.addBreadcrumb({
        category: feature,
        message,
        level: "info",
        data,
      }),
  };
}
