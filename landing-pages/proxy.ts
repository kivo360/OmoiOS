import { NextRequest, NextResponse } from "next/server"

// Subdomain to path mapping
const SUBDOMAIN_ROUTES: Record<string, string> = {
  openclaw: "/openclaw",
  // Add more subdomains here as needed:
  // "docs": "/docs",
  // "blog": "/blog",
}

export function proxy(request: NextRequest) {
  const url = request.nextUrl.clone()
  const hostname = request.headers.get("host") || ""

  // Extract subdomain (handles both production and localhost)
  // Production: openclaw.omoios.dev -> "openclaw"
  // Localhost: openclaw.localhost:3000 -> "openclaw"
  const subdomain = hostname.split(".")[0]

  // Skip if already on the correct path or if it's an asset/api request
  if (
    url.pathname.startsWith("/_next") ||
    url.pathname.startsWith("/api") ||
    url.pathname.includes(".")
  ) {
    return NextResponse.next()
  }

  // Check if this subdomain has a mapped route
  const mappedPath = SUBDOMAIN_ROUTES[subdomain]

  if (mappedPath) {
    // Rewrite root to the subdomain's page
    if (url.pathname === "/") {
      url.pathname = mappedPath
      return NextResponse.rewrite(url)
    }

    // For non-root paths on subdomain, prepend the mapped path if not already there
    if (!url.pathname.startsWith(mappedPath)) {
      url.pathname = `${mappedPath}${url.pathname}`
      return NextResponse.rewrite(url)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    // Match all paths except static files and api routes
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
}
