import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

const IS_DEV = process.env.NODE_ENV === "development";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Only generate browser source maps in production (saves memory in dev)
  productionBrowserSourceMaps: !IS_DEV,

  // Tree-shake barrel exports — only load the icons/components actually used
  // instead of the entire library. Massive memory savings in dev.
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@tabler/icons-react',
      'recharts',
      'framer-motion',
      'motion',
      '@radix-ui/react-accordion',
      '@radix-ui/react-alert-dialog',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-navigation-menu',
      '@radix-ui/react-popover',
      '@radix-ui/react-select',
      '@radix-ui/react-tabs',
      '@radix-ui/react-toast',
      '@radix-ui/react-tooltip',
      'date-fns',
      '@xyflow/react',
      'reactflow',
    ],
  },
}

// In development, skip Sentry wrapping entirely to save memory
let finalConfig = withMDX(nextConfig);

if (!IS_DEV) {
  const { withSentryConfig } = await import("@sentry/nextjs");

  finalConfig = withSentryConfig(finalConfig, {
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    authToken: process.env.SENTRY_AUTH_TOKEN,
    silent: !process.env.CI,
    hideSourceMaps: true,
    deleteSourcemapsAfterUpload: true,
    dryRun: !process.env.SENTRY_AUTH_TOKEN,
    tunnelRoute: "/api/monitoring/sentry",
    release: {
      create: true,
      finalize: true,
      name: process.env.SENTRY_RELEASE || process.env.VERCEL_GIT_COMMIT_SHA,
    },
    sourcemaps: {
      disable: false,
    },
  });
}

export default finalConfig;
