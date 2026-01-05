/**
 * Next.js Instrumentation
 *
 * This file is automatically loaded by Next.js to initialize
 * monitoring and observability tools like Sentry.
 *
 * @see https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */

export async function register() {
  // Import Sentry configs based on runtime
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config")
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config")
  }
}

/**
 * Error handler for uncaught errors during request handling
 * Sentry's Next.js SDK will automatically capture these
 */
export const onRequestError = async (
  error: Error,
  request: {
    path: string
    method: string
    headers: Record<string, string>
  },
  context: {
    routerKind: "Pages Router" | "App Router"
    routePath: string
    routeType: "render" | "route" | "action" | "middleware"
    renderSource?: "react-server-components" | "react-server-components-payload" | "server-rendering"
    revalidateReason?: "on-demand" | "stale" | undefined
    serverComponentType?: "layout" | "page" | "not-found" | "global-error"
  }
) => {
  // Sentry will automatically capture this via the SDK
  // This hook allows custom handling if needed
  const { captureException } = await import("@sentry/nextjs")

  captureException(error, {
    tags: {
      routerKind: context.routerKind,
      routeType: context.routeType,
      renderSource: context.renderSource,
    },
    extra: {
      path: request.path,
      method: request.method,
      routePath: context.routePath,
      revalidateReason: context.revalidateReason,
      serverComponentType: context.serverComponentType,
    },
  })
}
