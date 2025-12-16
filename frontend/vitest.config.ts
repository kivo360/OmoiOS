import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./__tests__/setup.tsx"],
    include: ["__tests__/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["__tests__/e2e/**/*", "node_modules/**/*"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        "__tests__/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/types.ts",
      ],
    },
    testTimeout: 10000,
    hookTimeout: 10000,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
    },
  },
})
