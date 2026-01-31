import { withSentryConfig } from "@sentry/nextjs"
import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Sentry configuration for source maps
  // Source maps allow Sentry to show original TypeScript code in stack traces
  productionBrowserSourceMaps: true,
}

// Sentry webpack plugin options
// @see https://github.com/getsentry/sentry-webpack-plugin#options
const sentryWebpackPluginOptions = {
  // Organization and project from environment variables
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Auth token for uploading source maps
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // Upload source maps only in CI/production builds
  silent: !process.env.CI,

  // Suppress all logs in development
  hideSourceMaps: true,

  // Automatically delete source maps after upload for security
  deleteSourcemapsAfterUpload: true,

  // Disable source map upload if no auth token (local development)
  dryRun: !process.env.SENTRY_AUTH_TOKEN,

  // Route tunnel through Next.js to avoid ad-blockers
  // This proxies Sentry requests through your domain
  tunnelRoute: "/api/monitoring/sentry",

  // Automatically instrument components
  automaticVercelMonitors: true,

  // Enable release management
  release: {
    // Create release in Sentry
    create: true,
    // Finalize release after deploy
    finalize: true,
    // Set release name from Git commit or env var
    name: process.env.SENTRY_RELEASE || process.env.VERCEL_GIT_COMMIT_SHA,
  },

  // Source maps configuration
  sourcemaps: {
    // Disable source map generation warnings
    disable: false,
  },
}

// Wrap with MDX first, then Sentry
// This enables Fumadocs MDX processing and Sentry error capturing
export default withSentryConfig(
  withMDX(nextConfig),
  sentryWebpackPluginOptions
)
