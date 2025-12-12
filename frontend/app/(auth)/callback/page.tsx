"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import { useAuth } from "@/hooks/useAuth"
import { setTokens, clearTokens } from "@/lib/api/client"
import { getCurrentUser } from "@/lib/api/auth"

type CallbackStatus = "loading" | "success" | "error"

function CallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login } = useAuth()
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<CallbackStatus>("loading")
  const [errorMessage, setErrorMessage] = useState<string>("")
  const [provider, setProvider] = useState<string>("")

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error from OAuth provider
      const error = searchParams.get("error")
      if (error) {
        setStatus("error")
        setErrorMessage(error.replace(/_/g, " "))
        setTimeout(() => router.push(`/login?error=${error}`), 3000)
        return
      }

      // Get tokens from URL
      const accessToken = searchParams.get("access_token")
      const refreshToken = searchParams.get("refresh_token")
      const providerName = searchParams.get("provider")

      if (providerName) {
        setProvider(providerName)
      }

      if (!accessToken || !refreshToken) {
        setStatus("error")
        setErrorMessage("No authentication tokens received")
        setTimeout(() => router.push("/login?error=no_tokens"), 3000)
        return
      }

      try {
        // Store tokens
        setTokens(accessToken, refreshToken)

        // Fetch user info
        const user = await getCurrentUser()

        // Update auth context
        login(user)
        
        // Invalidate OAuth-related queries to refresh connection status
        queryClient.invalidateQueries({ queryKey: ["oauth", "connected"] })
        queryClient.invalidateQueries({ queryKey: ["github-repos"] })
        
        setStatus("success")

        // Redirect to main app after brief success display
        setTimeout(() => router.push("/command"), 1500)
      } catch (err) {
        console.error("OAuth callback error:", err)
        setStatus("error")
        setErrorMessage("Failed to complete authentication")
        clearTokens()
        setTimeout(() => router.push("/login?error=auth_failed"), 3000)
      }
    }

    handleCallback()
  }, [searchParams, router, login, queryClient])

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center text-center space-y-4">
        {status === "loading" && (
          <>
            <div className="rounded-full bg-primary/10 p-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
            <div>
              <CardTitle className="text-xl">Completing sign in...</CardTitle>
              <CardDescription className="mt-2">
                {provider
                  ? `Authenticating with ${provider.charAt(0).toUpperCase() + provider.slice(1)}`
                  : "Please wait while we verify your credentials"}
              </CardDescription>
            </div>
          </>
        )}

        {status === "success" && (
          <>
            <div className="rounded-full bg-green-500/10 p-4">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <div>
              <CardTitle className="text-xl text-green-500">
                Sign in successful!
              </CardTitle>
              <CardDescription className="mt-2">
                Redirecting to your dashboard...
              </CardDescription>
            </div>
          </>
        )}

        {status === "error" && (
          <>
            <div className="rounded-full bg-destructive/10 p-4">
              <XCircle className="h-8 w-8 text-destructive" />
            </div>
            <div>
              <CardTitle className="text-xl text-destructive">
                Sign in failed
              </CardTitle>
              <CardDescription className="mt-2">
                {errorMessage || "An error occurred during authentication"}
              </CardDescription>
              <p className="text-sm text-muted-foreground mt-4">
                Redirecting to login page...
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="flex flex-col items-center justify-center text-center space-y-4">
            <div className="rounded-full bg-primary/10 p-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
            <div>
              <CardTitle className="text-xl">Loading...</CardTitle>
            </div>
          </div>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  )
}
