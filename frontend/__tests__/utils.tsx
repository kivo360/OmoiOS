import React, { ReactElement } from "react"
import { render, RenderOptions } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

/**
 * Creates a fresh QueryClient for testing
 * - Disables retries to make tests deterministic
 * - Disables garbage collection during tests
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

/**
 * All providers needed for testing components
 */
interface TestProvidersProps {
  children: React.ReactNode
  queryClient?: QueryClient
}

export function TestProviders({
  children,
  queryClient,
}: TestProvidersProps) {
  const client = queryClient ?? createTestQueryClient()

  return (
    <QueryClientProvider client={client}>
      {children}
    </QueryClientProvider>
  )
}

/**
 * Custom render function that wraps components with all necessary providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient
}

function customRender(
  ui: ReactElement,
  options?: CustomRenderOptions
) {
  const { queryClient, ...renderOptions } = options ?? {}

  return render(ui, {
    wrapper: ({ children }) => (
      <TestProviders queryClient={queryClient}>{children}</TestProviders>
    ),
    ...renderOptions,
  })
}

/**
 * Creates a wrapper component for testing hooks
 */
export function createWrapper(queryClient?: QueryClient) {
  const client = queryClient ?? createTestQueryClient()
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )
  }
}

// Re-export everything from testing-library
export * from "@testing-library/react"
export { userEvent } from "@testing-library/user-event"

// Override render with custom render
export { customRender as render }

// Export query client creator for advanced use cases
export { createTestQueryClient }
