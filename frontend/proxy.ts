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
  "/docs",
  "/blog",
  "/feed.xml",
  "/sitemap.xml",
  "/robots.txt",
]

// Routes exempt from onboarding enforcement
// These routes are accessible even if onboarding is not complete
const ONBOARDING_EXEMPT_ROUTES = [
  "/onboarding",
  "/callback",
  "/logout",
  "/api",
  "/settings", // Allow settings access during onboarding
]

// Cookie name that indicates auth state (set by client after login)
const AUTH_COOKIE_NAME = "omoios_auth_state"

// Cookie name that indicates onboarding completion (set by client after sync)
const ONBOARDING_COOKIE_NAME = "omoios_onboarding_completed"

/**
 * Next.js 16 Proxy - runs before routes are rendered
 * Handles authentication and onboarding redirects at the edge for instant navigation
 */
export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check for auth cookie
  const authCookie = request.cookies.get(AUTH_COOKIE_NAME)
  const isAuthenticated = authCookie?.value === "true"

  // Check for onboarding completion cookie
  const onboardingCookie = request.cookies.get(ONBOARDING_COOKIE_NAME)
  const onboardingCompleted = onboardingCookie?.value === "true"

  // Check route types
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route))
  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname.startsWith(route))
  const isOnboardingExempt = ONBOARDING_EXEMPT_ROUTES.some((route) =>
    pathname.startsWith(route)
  )
  const isOnboardingRoute = pathname.startsWith("/onboarding")
  const isRootRoute = pathname === "/"

  // If authenticated and trying to access auth routes -> redirect to appropriate place
  // This is the KEY optimization - redirect happens at edge before React loads
  if (isAuthenticated && isAuthRoute) {
    // If onboarding not complete, redirect to onboarding instead of command
    if (!onboardingCompleted) {
      return NextResponse.redirect(new URL("/onboarding", request.url))
    }
    return NextResponse.redirect(new URL("/command", request.url))
  }

  // If not authenticated and trying to access protected routes -> redirect to /login
  if (!isAuthenticated && !isPublicRoute && !isOnboardingRoute && !isRootRoute) {
    const url = new URL("/login", request.url)
    // Preserve the original URL to redirect back after login
    url.searchParams.set("from", pathname)
    return NextResponse.redirect(url)
  }

  // If authenticated but onboarding not complete -> redirect to onboarding
  // (except for exempt routes like callback, api, settings)
  if (isAuthenticated && !onboardingCompleted && !isOnboardingExempt && !isPublicRoute && !isRootRoute) {
    return NextResponse.redirect(new URL("/onboarding", request.url))
  }

  // If authenticated, onboarding complete, and trying to access /onboarding -> redirect to command
  // (Allow users to access onboarding if they explicitly want to, via query param)
  if (isAuthenticated && onboardingCompleted && isOnboardingRoute) {
    const forceOnboarding = request.nextUrl.searchParams.get("force") === "true"
    if (!forceOnboarding) {
      return NextResponse.redirect(new URL("/command", request.url))
    }
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
    "/((?!api|_next/static|_next/image|opengraph-image|opengraph-image-light|og/|twitter-image|robots\\.txt|sitemap\\.xml|site\\.webmanifest|manifest\\.json|apple-touch-icon|favicon|icon-|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|xml|json|txt|mp4|webm)$).*)",
  ],
}
