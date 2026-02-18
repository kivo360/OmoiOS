"use client";

/**
 * Global Error Handler
 *
 * This is the root error boundary for the entire Next.js application.
 * It catches errors that escape from all other error boundaries,
 * including errors in the root layout.
 *
 * This component MUST define its own <html> and <body> tags because
 * it replaces the root layout when an error occurs.
 *
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling#handling-errors-in-root-layouts
 */

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    // Report the error to Sentry
    Sentry.captureException(error, {
      tags: {
        "error.boundary": "global",
        "error.category": "fatal",
      },
      extra: {
        digest: error.digest,
      },
    });
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-background text-foreground antialiased">
        <div className="flex min-h-screen flex-col items-center justify-center p-4">
          <div className="w-full max-w-md rounded-lg border bg-card p-8 text-center shadow-lg">
            {/* Error Icon */}
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="h-8 w-8 text-destructive" />
            </div>

            {/* Error Message */}
            <h1 className="mb-2 text-2xl font-bold tracking-tight">
              Something went wrong
            </h1>
            <p className="mb-6 text-muted-foreground">
              We encountered an unexpected error. Our team has been
              automatically notified and is working to fix it.
            </p>

            {/* Error Details (development only) */}
            {process.env.NODE_ENV === "development" && (
              <div className="mb-6 rounded-md bg-muted p-4 text-left">
                <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                  Error Details
                </p>
                <p className="break-all font-mono text-sm text-destructive">
                  {error.message}
                </p>
                {error.digest && (
                  <p className="mt-2 font-mono text-xs text-muted-foreground">
                    Digest: {error.digest}
                  </p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <button
                onClick={reset}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Try again
              </button>
              <a
                href="/"
                className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Home className="mr-2 h-4 w-4" />
                Go home
              </a>
            </div>

            {/* Support Link */}
            <p className="mt-6 text-xs text-muted-foreground">
              If this problem persists, please{" "}
              <a
                href="mailto:support@omoios.dev"
                className="text-primary underline-offset-4 hover:underline"
              >
                contact support
              </a>
            </p>
          </div>
        </div>

        {/* Inline styles for when CSS fails to load */}
        <style>{`
          :root {
            --background: 0 0% 100%;
            --foreground: 222.2 84% 4.9%;
            --card: 0 0% 100%;
            --card-foreground: 222.2 84% 4.9%;
            --primary: 222.2 47.4% 11.2%;
            --primary-foreground: 210 40% 98%;
            --muted: 210 40% 96.1%;
            --muted-foreground: 215.4 16.3% 46.9%;
            --destructive: 0 84.2% 60.2%;
            --border: 214.3 31.8% 91.4%;
            --input: 214.3 31.8% 91.4%;
            --ring: 222.2 84% 4.9%;
            --accent: 210 40% 96.1%;
            --accent-foreground: 222.2 47.4% 11.2%;
          }

          @media (prefers-color-scheme: dark) {
            :root {
              --background: 222.2 84% 4.9%;
              --foreground: 210 40% 98%;
              --card: 222.2 84% 4.9%;
              --card-foreground: 210 40% 98%;
              --primary: 210 40% 98%;
              --primary-foreground: 222.2 47.4% 11.2%;
              --muted: 217.2 32.6% 17.5%;
              --muted-foreground: 215 20.2% 65.1%;
              --destructive: 0 62.8% 30.6%;
              --border: 217.2 32.6% 17.5%;
              --input: 217.2 32.6% 17.5%;
              --ring: 212.7 26.8% 83.9%;
              --accent: 217.2 32.6% 17.5%;
              --accent-foreground: 210 40% 98%;
            }
          }

          body {
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          }

          .bg-background { background-color: hsl(var(--background)); }
          .bg-card { background-color: hsl(var(--card)); }
          .bg-muted { background-color: hsl(var(--muted)); }
          .bg-primary { background-color: hsl(var(--primary)); }
          .bg-destructive\\/10 { background-color: hsl(var(--destructive) / 0.1); }
          .text-foreground { color: hsl(var(--foreground)); }
          .text-muted-foreground { color: hsl(var(--muted-foreground)); }
          .text-primary { color: hsl(var(--primary)); }
          .text-primary-foreground { color: hsl(var(--primary-foreground)); }
          .text-destructive { color: hsl(var(--destructive)); }
          .border { border-color: hsl(var(--border)); }
          .border-input { border-color: hsl(var(--input)); }
        `}</style>
      </body>
    </html>
  );
}
