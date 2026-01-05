import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Auth routes - redirect to /command if already authenticated
const AUTH_ROUTES = ["/login", "/register"]

// Public routes - accessible without authentication
const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/callback",
]

// Cookie name that indicates auth state (set by client after login)
const AUTH_COOKIE_NAME = "omoios_auth_state"

/**
 * Next.js 16 Proxy - runs before routes are rendered
 * Handles authentication redirects at the edge for instant navigation
 */
export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check for auth cookie
  const authCookie = request.cookies.get(AUTH_COOKIE_NAME)
  const isAuthenticated = authCookie?.value === "true"

  // Check route types
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route))
  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname.startsWith(route))
  const isRootRoute = pathname === "/"

  // If authenticated and trying to access auth routes -> redirect to /command
  // This is the KEY optimization - redirect happens at edge before React loads
  if (isAuthenticated && isAuthRoute) {
    return NextResponse.redirect(new URL("/command", request.url))
  }

  // If not authenticated and trying to access protected routes -> redirect to /login
  if (!isAuthenticated && !isPublicRoute && !isRootRoute) {
    const url = new URL("/login", request.url)
    // Preserve the original URL to redirect back after login
    url.searchParams.set("from", pathname)
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes (API handlers)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - Static assets (svg, png, jpg, etc.)
     * - SEO/Crawler files (robots.txt, sitemap.xml, manifest)
     * - OpenGraph/Twitter images (social media crawlers need access)
     * - Apple touch icons and favicons
     */
    "/((?!api|_next/static|_next/image|opengraph-image|twitter-image|robots\\.txt|sitemap\\.xml|site\\.webmanifest|manifest\\.json|apple-touch-icon|favicon|icon-|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|xml|json|txt)$).*)",
  ],
}
