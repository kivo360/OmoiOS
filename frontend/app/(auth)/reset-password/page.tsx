"use client"

import { useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { ArrowLeft, Loader2, CheckCircle, CheckCircle2, XCircle } from "lucide-react"
import { resetPassword } from "@/lib/api/auth"
import { ApiError } from "@/lib/api/client"

// Password requirements (same as register)
const PASSWORD_REQUIREMENTS = [
  { id: "length", label: "At least 8 characters", test: (p: string) => p.length >= 8 },
  { id: "uppercase", label: "One uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { id: "lowercase", label: "One lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { id: "number", label: "One number", test: (p: string) => /\d/.test(p) },
]

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
  })
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState("")
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false)

  // Check which password requirements are met
  const passwordChecks = PASSWORD_REQUIREMENTS.map((req) => ({
    ...req,
    met: req.test(formData.password),
  }))

  const allPasswordRequirementsMet = passwordChecks.every((check) => check.met)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match")
      setIsLoading(false)
      return
    }

    if (!allPasswordRequirementsMet) {
      setError("Password does not meet all requirements")
      setIsLoading(false)
      return
    }

    try {
      await resetPassword({
        token: token!,
        new_password: formData.password,
      })

      setIsSuccess(true)
      setTimeout(() => {
        router.push("/login")
      }, 3000)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError("Failed to reset password. Please try again.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="space-y-6 text-center">
        <CardTitle className="text-2xl">Invalid Link</CardTitle>
        <CardDescription>
          This password reset link is invalid or has expired.
        </CardDescription>
        <Button asChild className="w-full">
          <Link href="/forgot-password">Request a new link</Link>
        </Button>
      </div>
    )
  }

  if (isSuccess) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
          <CheckCircle className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <CardTitle className="text-2xl">Password reset!</CardTitle>
          <CardDescription className="mt-2">
            Your password has been successfully reset. Redirecting to login...
          </CardDescription>
        </div>
        <Button asChild className="w-full">
          <Link href="/login">Go to login</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Reset your password</CardTitle>
        <CardDescription>Enter your new password below</CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="password">New Password</Label>
          <Input
            id="password"
            type="password"
            placeholder="Create a strong password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            onFocus={() => setShowPasswordRequirements(true)}
            required
            disabled={isLoading}
            autoComplete="new-password"
          />
          
          {/* Password requirements checklist */}
          {showPasswordRequirements && formData.password && (
            <div className="mt-2 space-y-1 text-xs">
              {passwordChecks.map((check) => (
                <div
                  key={check.id}
                  className={`flex items-center gap-2 ${
                    check.met ? "text-green-600" : "text-muted-foreground"
                  }`}
                >
                  {check.met ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
                  )}
                  {check.label}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm New Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            placeholder="Confirm your new password"
            value={formData.confirmPassword}
            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
            required
            disabled={isLoading}
            autoComplete="new-password"
          />
          {formData.confirmPassword && formData.password !== formData.confirmPassword && (
            <p className="text-xs text-destructive">Passwords do not match</p>
          )}
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading || !allPasswordRequirementsMet}
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isLoading ? "Resetting..." : "Reset password"}
        </Button>
      </form>

      <div className="text-center">
        <Link
          href="/login"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to login
        </Link>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="text-center"><Loader2 className="mx-auto h-8 w-8 animate-spin" /></div>}>
      <ResetPasswordForm />
    </Suspense>
  )
}
