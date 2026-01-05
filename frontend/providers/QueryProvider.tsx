"use client"

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { useState } from "react"
import * as Sentry from "@sentry/nextjs"
import { ApiError } from "@/lib/api/client"

/**
 * Handle React Query errors and report to Sentry
 */
function handleQueryError(error: unknown, queryKey?: unknown) {
  // Skip reporting for expected errors (handled in UI)
  if (error instanceof ApiError) {
    // 401/403 are handled by auth flow
    if (error.status === 401 || error.status === 403) {
      return
    }
    // 404 is often expected (checking if resource exists)
    if (error.status === 404) {
      return
    }
  }

  // Report unexpected errors to Sentry
  Sentry.withScope((scope) => {
    scope.setTag("error.category", "react-query")
    scope.setTag("error.type", "query")

    if (queryKey) {
      scope.setExtra("queryKey", JSON.stringify(queryKey))
    }

    if (error instanceof Error) {
      Sentry.captureException(error)
    }
  })
}

function handleMutationError(error: unknown, variables?: unknown, mutationKey?: unknown) {
  // Skip reporting for expected errors
  if (error instanceof ApiError) {
    // Validation errors are handled in UI
    if (error.status === 400 || error.status === 422) {
      return
    }
    // Auth errors handled by auth flow
    if (error.status === 401 || error.status === 403) {
      return
    }
  }

  // Report unexpected mutation errors
  Sentry.withScope((scope) => {
    scope.setTag("error.category", "react-query")
    scope.setTag("error.type", "mutation")

    if (mutationKey) {
      scope.setExtra("mutationKey", JSON.stringify(mutationKey))
    }

    // Don't include variables - may contain sensitive data
    if (error instanceof Error) {
      Sentry.captureException(error)
    }
  })
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error, query) => {
            handleQueryError(error, query.queryKey)
          },
        }),
        mutationCache: new MutationCache({
          onError: (error, variables, _context, mutation) => {
            handleMutationError(error, variables, mutation.options.mutationKey)
          },
        }),
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
