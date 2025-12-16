import React from "react"
import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeAll, afterAll, vi } from "vitest"
import { server } from "./mocks/server"

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: "warn" })
})

// Reset any request handlers between tests
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Clean up after all tests
afterAll(() => {
  server.close()
})

// Mock Next.js router
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: function Link({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) {
    return <a href={href} {...props}>{children}</a>
  },
}))

// Mock next-themes
vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "light",
    setTheme: vi.fn(),
    resolvedTheme: "light",
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))
