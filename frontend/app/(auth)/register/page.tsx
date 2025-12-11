"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Github, Mail, Loader2, CheckCircle2, XCircle } from "lucide-react"
import { register as apiRegister } from "@/lib/api/auth"
import { ApiError } from "@/lib/api/client"
import { startOAuthFlow } from "@/lib/api/oauth"

// Password requirements
const PASSWORD_REQUIREMENTS = [
  { id: "length", label: "At least 8 characters", test: (p: string) => p.length >= 8 },
  { id: "uppercase", label: "One uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { id: "lowercase", label: "One lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { id: "number", label: "One number", test: (p: string) => /\d/.test(p) },
]

export default function RegisterPage() {
  const router = useRouter()
  
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  const [isLoading, setIsLoading] = useState(false)
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

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match")
      setIsLoading(false)
      return
    }

    // Validate password strength
    if (!allPasswordRequirementsMet) {
      setError("Password does not meet all requirements")
      setIsLoading(false)
      return
    }

    try {
      await apiRegister({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name || undefined,
      })

      // Redirect to verify email page
      router.push("/verify-email?email=" + encodeURIComponent(formData.email))
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError("Registration failed. Please try again.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleOAuth = (provider: "github" | "google") => {
    try {
      startOAuthFlow(provider)
    } catch (error) {
      console.error(`Failed to start OAuth flow for ${provider}:`, error)
      setError(`Failed to start ${provider} authentication. Please try again.`)
    }
  }

  const updateFormData = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Create an account</CardTitle>
        <CardDescription>Get started with OmoiOS today</CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="full_name">Full Name</Label>
          <Input
            id="full_name"
            type="text"
            placeholder="John Doe"
            value={formData.full_name}
            onChange={(e) => updateFormData("full_name", e.target.value)}
            disabled={isLoading}
            autoComplete="name"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={(e) => updateFormData("email", e.target.value)}
            required
            disabled={isLoading}
            autoComplete="email"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            placeholder="Create a strong password"
            value={formData.password}
            onChange={(e) => updateFormData("password", e.target.value)}
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
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            placeholder="Confirm your password"
            value={formData.confirmPassword}
            onChange={(e) => updateFormData("confirmPassword", e.target.value)}
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
          {isLoading ? "Creating account..." : "Create account"}
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <Separator />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Button
          type="button"
          variant="outline"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            handleOAuth("github")
          }}
          disabled={isLoading}
        >
          <Github className="mr-2 h-4 w-4" />
          GitHub
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            handleOAuth("google")
          }}
          disabled={isLoading}
        >
          <Mail className="mr-2 h-4 w-4" />
          Google
        </Button>
      </div>

      <div className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-primary hover:underline">
          Sign in
        </Link>
      </div>
    </div>
  )
}
