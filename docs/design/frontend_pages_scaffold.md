# Frontend Pages Scaffold

**Created**: 2025-05-19
**Status**: Scaffold Document
**Purpose**: Provides copy-paste ready Next.js 15 page code (App Router) integrating the scaffolded components.

---

## 1. Authentication Pages

### `app/(auth)/layout.tsx`

Auth layout wrapper with centered card design.

```tsx
import { Card } from "@/components/ui/card"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/10 p-4">
      <Card className="w-full max-w-md p-6">
        {children}
      </Card>
    </div>
  )
}
```

### `app/(auth)/login/page.tsx`

Login page with email/password and OAuth options.

```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { useRouter } from "next/navigation"
import { Github, Mail } from "lucide-react"
import Link from "next/link"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || "Login failed")
      }

      const data = await res.json()
      // Store token (e.g., in localStorage or httpOnly cookie)
      localStorage.setItem("auth_token", data.token)
      
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOAuth = (provider: "github" | "google") => {
    window.location.href = `/api/v1/auth/oauth/${provider}`
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to your account to continue</CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link
              href="/auth/forgot-password"
              className="text-sm text-primary hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <Separator />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Button
          type="button"
          variant="outline"
          onClick={() => handleOAuth("github")}
          disabled={isLoading}
        >
          <Github className="mr-2 h-4 w-4" />
          GitHub
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => handleOAuth("google")}
          disabled={isLoading}
        >
          <Mail className="mr-2 h-4 w-4" />
          Google
        </Button>
      </div>

      <div className="text-center text-sm text-muted-foreground">
        Don't have an account?{" "}
        <Link href="/auth/register" className="text-primary hover:underline">
          Sign up
        </Link>
      </div>
    </div>
  )
}
```

### `app/(auth)/register/page.tsx`

Registration page with email/password and OAuth options.

```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { useRouter } from "next/navigation"
import { Github, Mail } from "lucide-react"
import Link from "next/link"

export default function RegisterPage() {
  const router = useRouter()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }

    setIsLoading(true)

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || "Registration failed")
      }

      const data = await res.json()
      localStorage.setItem("auth_token", data.token)
      
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOAuth = (provider: "github" | "google") => {
    window.location.href = `/api/v1/auth/oauth/${provider}`
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Create an account</CardTitle>
        <CardDescription>Enter your information to get started</CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            type="text"
            placeholder="John Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            minLength={8}
          />
          <p className="text-xs text-muted-foreground">
            Must be at least 8 characters
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Creating account..." : "Create account"}
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <Separator />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Button
          type="button"
          variant="outline"
          onClick={() => handleOAuth("github")}
          disabled={isLoading}
        >
          <Github className="mr-2 h-4 w-4" />
          GitHub
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => handleOAuth("google")}
          disabled={isLoading}
        >
          <Mail className="mr-2 h-4 w-4" />
          Google
        </Button>
      </div>

      <div className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/auth/login" className="text-primary hover:underline">
          Sign in
        </Link>
      </div>
    </div>
  )
}
```

### `app/(auth)/forgot-password/page.tsx`

Password reset request page.

```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { CheckCircle2 } from "lucide-react"
import Link from "next/link"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSent, setIsSent] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || "Failed to send reset email")
      }

      setIsSent(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  if (isSent) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <CheckCircle2 className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <CardTitle className="text-2xl">Check your email</CardTitle>
          <CardDescription className="mt-2">
            We've sent a password reset link to {email}
          </CardDescription>
        </div>
        <Link href="/auth/login" className="text-sm text-primary hover:underline">
          Back to login
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Forgot password?</CardTitle>
        <CardDescription>
          Enter your email address and we'll send you a link to reset your password
        </CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Sending..." : "Send reset link"}
        </Button>
      </form>

      <div className="text-center text-sm text-muted-foreground">
        <Link href="/auth/login" className="text-primary hover:underline">
          Back to login
        </Link>
      </div>
    </div>
  )
}
```

### `app/(auth)/reset-password/[token]/page.tsx`

Password reset page with token validation.

```tsx
"use client"

import { use } from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { useRouter } from "next/navigation"
import { CheckCircle2 } from "lucide-react"

export default function ResetPasswordPage({
  params,
}: {
  params: Promise<{ token: string }>
}) {
  const { token } = use(params)
  const router = useRouter()
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }

    setIsLoading(true)

    try {
      const res = await fetch("/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || "Failed to reset password")
      }

      setIsSuccess(true)
      setTimeout(() => {
        router.push("/auth/login")
      }, 2000)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  if (isSuccess) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <CheckCircle2 className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <CardTitle className="text-2xl">Password reset successful</CardTitle>
          <CardDescription className="mt-2">
            Redirecting to login...
          </CardDescription>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CardTitle className="text-2xl">Reset your password</CardTitle>
        <CardDescription>
          Enter your new password below
        </CardDescription>
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            minLength={8}
          />
          <p className="text-xs text-muted-foreground">
            Must be at least 8 characters
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Resetting..." : "Reset password"}
        </Button>
      </form>
    </div>
  )
}
```

### `app/(auth)/oauth/callback/page.tsx`

OAuth callback handler for GitHub/Google.

```tsx
"use client"

import { useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [error, setError] = useState("")

  useEffect(() => {
    const code = searchParams.get("code")
    const state = searchParams.get("state")
    const provider = searchParams.get("provider") || "github"

    if (!code) {
      setError("Missing authorization code")
      return
    }

    const handleCallback = async () => {
      try {
        const res = await fetch("/api/v1/auth/oauth/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, state, provider }),
        })

        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.message || "OAuth authentication failed")
        }

        const data = await res.json()
        localStorage.setItem("auth_token", data.token)
        
        router.push("/dashboard")
      } catch (err: any) {
        setError(err.message)
      }
    }

    handleCallback()
  }, [searchParams, router])

  if (error) {
    return (
      <div className="space-y-6 text-center">
        <CardTitle className="text-2xl text-destructive">Authentication failed</CardTitle>
        <CardDescription>{error}</CardDescription>
        <Button onClick={() => router.push("/auth/login")}>
          Back to login
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 text-center">
      <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
      <CardTitle className="text-2xl">Completing authentication...</CardTitle>
      <CardDescription>Please wait while we sign you in</CardDescription>
    </div>
  )
}
```

---

## 2. Dashboard Shell

### `app/(dashboard)/layout.tsx`

Root layout for the authenticated dashboard area with auth protection.

```tsx
import { AppSidebar } from "@/components/layout/AppSidebar"
import { TopHeader } from "@/components/layout/TopHeader" 
import { AuthGuard } from "@/components/auth/AuthGuard"
import { Toaster } from "@/components/ui/toaster"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-muted/10">
        {/* Sidebar */}
        <AppSidebar className="hidden md:block fixed inset-y-0 z-50" />
        
        <div className="flex flex-col flex-1 md:pl-64 transition-all duration-300">
          {/* Top Header */}
          <TopHeader />
          
          {/* Main Content */}
          <main className="flex-1 p-6 overflow-y-auto">
            {children}
          </main>
        </div>
        <Toaster />
      </div>
    </AuthGuard>
  )
}
```

### `app/(dashboard)/overview/page.tsx`

System overview dashboard.

```tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Activity, CheckCircle2, AlertTriangle } from "lucide-react"

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">System Overview</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Coherence</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">92%</div>
            <p className="text-xs text-muted-foreground">
              +2% from last hour
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground">
              Working on 3 projects
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Issues</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">
              Requires attention
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-8">
              {/* Placeholder for Activity Feed */}
              <div className="flex items-center">
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">Agent X completed Task Y</p>
                  <p className="text-sm text-muted-foreground">2 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Active Projects</CardTitle>
            <CardDescription>
              Currently running initiatives.
            </CardDescription>
          </CardHeader>
          <CardContent>
             {/* Placeholder for mini project list */}
             <div className="space-y-4">
               <div className="flex items-center justify-between">
                 <div className="font-medium">Auth System</div>
                 <div className="text-sm text-green-600">Healthy</div>
               </div>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

---

## 2. Project Pages

### `app/(dashboard)/projects/page.tsx`

Lists all projects.

```tsx
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ProjectCard } from "@/components/project/ProjectCard"
import { CreateProjectDialog } from "@/components/project/CreateProjectDialog"
import { Search } from "lucide-react"

// Mock data fetcher
async function getProjects() {
  return [
    {
      id: "1",
      name: "Authentication System",
      description: "Multi-provider authentication system with OAuth2.",
      status: "active" as const,
      progress: 0.45,
      ticketCount: 24,
      agentCount: 5
    },
    {
      id: "2",
      name: "User Profile Management",
      description: "Self-service profile editor.",
      status: "active" as const,
      progress: 0.15,
      ticketCount: 12,
      agentCount: 2
    }
  ]
}

export default async function ProjectsPage() {
  const projects = await getProjects()

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">
            Manage your ongoing projects and initiatives.
          </p>
        </div>
        <CreateProjectDialog />
      </div>

      <div className="flex items-center space-x-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search projects..."
            className="pl-8"
          />
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  )
}
```

### `app/(dashboard)/projects/[projectId]/layout.tsx`

Project context layout.

```tsx
import Link from "next/link"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { projectId: string }
}) {
  const { projectId } = params

  return (
    <div className="flex flex-col gap-6 h-full">
      <div className="border-b pb-2">
        <div className="mb-4">
          <h1 className="text-2xl font-bold tracking-tight">Project: Authentication System</h1>
          <p className="text-muted-foreground text-sm">ID: {projectId}</p>
        </div>
        <Tabs defaultValue="overview" className="w-full">
          <TabsList>
            <TabsTrigger value="overview" asChild>
              <Link href={`/projects/${projectId}`}>Overview</Link>
            </TabsTrigger>
            <TabsTrigger value="board" asChild>
              <Link href={`/projects/${projectId}/board`}>Board</Link>
            </TabsTrigger>
            <TabsTrigger value="graph" asChild>
              <Link href={`/projects/${projectId}/graph`}>Graph</Link>
            </TabsTrigger>
            <TabsTrigger value="explore" asChild>
              <Link href={`/projects/${projectId}/explore`}>Explore</Link>
            </TabsTrigger>
            <TabsTrigger value="settings" asChild>
              <Link href={`/projects/${projectId}/settings`}>Settings</Link>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="flex-1 min-h-0">
        {children}
      </div>
    </div>
  )
}
```

### `app/(dashboard)/projects/[projectId]/page.tsx`

Project overview.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

export default function ProjectOverviewPage({ params }: { params: { projectId: string } }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Tickets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$1,200</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Overall Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>45% Complete</span>
            </div>
            <Progress value={45} className="h-4" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

### `app/(dashboard)/projects/[projectId]/board/page.tsx`

Kanban board.

```tsx
"use client"

import { DndContext, DragOverlay, closestCorners } from "@dnd-kit/core"
import { useState } from "react"
import { BoardColumn } from "@/components/kanban/BoardColumn"
import { Button } from "@/components/ui/button"
import { Filter } from "lucide-react"
import { createPortal } from "react-dom"

// Mock data
const initialData = {
  columns: [
    { id: "backlog", title: "Backlog", tickets: [{ id: "T-1", title: "Setup Repo", description: "Init git", priority: "high", status: "backlog" }] },
    { id: "todo", title: "To Do", tickets: [] },
    { id: "in_progress", title: "In Progress", tickets: [{ id: "T-2", title: "Dev Auth", description: "Implement OAuth", priority: "critical", status: "in_progress" }] },
    { id: "done", title: "Done", tickets: [] },
  ]
}

export default function BoardPage({ params }: { params: { projectId: string } }) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [columns, setColumns] = useState(initialData.columns)

  function handleDragStart(event: any) {
    setActiveId(event.active.id)
  }

  function handleDragEnd(event: any) {
    setActiveId(null)
  }

  return (
    <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd} collisionDetection={closestCorners}>
      <div className="flex flex-col h-full gap-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Kanban Board</h2>
          <div className="flex gap-2">
             <Button variant="outline" size="sm">
               <Filter className="mr-2 h-4 w-4" /> Filter
             </Button>
             <Button size="sm">Add Ticket</Button>
          </div>
        </div>
        
        <div className="flex h-full gap-4 overflow-x-auto pb-4">
          {columns.map((col) => (
            <BoardColumn 
              key={col.id} 
              id={col.id} 
              title={col.title} 
              tickets={col.tickets} 
            />
          ))}
        </div>
      </div>

      {typeof document !== 'undefined' && createPortal(
        <DragOverlay>
          {activeId ? (
             <div className="p-4 bg-background border rounded shadow-lg opacity-80 rotate-2 cursor-grabbing">Dragging...</div>
          ) : null}
        </DragOverlay>,
        document.body
      )}
    </DndContext>
  )
}
```

### `app/(dashboard)/projects/[projectId]/graph/page.tsx`

Dependency graph view.

```tsx
import { GraphView } from "@/components/graph/GraphView"

export default function GraphPage() {
  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Dependency Graph</h2>
      </div>
      <div className="flex-1 border rounded-lg bg-background overflow-hidden">
        <GraphView />
      </div>
    </div>
  )
}
```

### `app/(dashboard)/projects/[projectId]/settings/page.tsx`

Project settings.

```tsx
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"

export default function ProjectSettingsPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input id="name" defaultValue="Authentication System" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="desc">Description</Label>
            <Input id="desc" defaultValue="Multi-provider authentication system..." />
          </div>
        </CardContent>
        <CardFooter>
          <Button>Save Changes</Button>
        </CardFooter>
      </Card>
      
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Deleting a project cannot be undone. All tickets and agent history will be lost.
          </p>
        </CardContent>
        <CardFooter>
          <Button variant="destructive">Delete Project</Button>
        </CardFooter>
      </Card>
    </div>
  )
}
```

---

## 3. Agent Pages

### `app/(dashboard)/agents/page.tsx`

List of all agents.

```tsx
import { AgentCard } from "@/components/agent/AgentCard"
import { Button } from "@/components/ui/button"

export default function AgentsPage() {
  const agents = [
    { id: "1", name: "Worker-Alpha", status: "active" as const, currentTask: "Implementing Login", capabilities: ["Python", "FastAPI"] },
    { id: "2", name: "Worker-Beta", status: "idle" as const, capabilities: ["React", "Next.js"] },
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
        <Button>Spawn Agent</Button>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {agents.map(agent => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  )
}
```

### `app/(dashboard)/agents/[agentId]/page.tsx`

Agent detail view.

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AuditTrailViewer } from "@/components/audit/AuditTrailViewer"

export default function AgentDetailPage({ params }: { params: { agentId: string } }) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            Worker-Alpha 
            <Badge>Active</Badge>
          </h1>
          <p className="text-muted-foreground">ID: {params.agentId}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Current Task</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium">Implement Login Endpoint</p>
            <p className="text-sm text-muted-foreground mt-2">
              Creating POST /api/login with JWT validation.
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Performance</CardTitle>
          </CardHeader>
          <CardContent>
             <div className="text-sm">
               <p>Tasks Completed: 15</p>
               <p>Success Rate: 95%</p>
             </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Activity Log</CardTitle>
        </CardHeader>
        <CardContent>
          <AuditTrailViewer events={[]} />
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## 17. Specs Management Pages

### `app/(dashboard)/projects/[projectId]/specs/page.tsx`

Specs list page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { SpecList } from "@/components/specs/SpecList"
import { DashboardLayout } from "@/components/layout/DashboardLayout"

export default function SpecsPage({ params }: { params: { projectId: string } }) {
  const { data: specs, isLoading } = useQuery({
    queryKey: ["specs", params.projectId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/projects/${params.projectId}/specs`)
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <DashboardLayout>
      <SpecList projectId={params.projectId} specs={specs || []} />
    </DashboardLayout>
  )
}
```

### `app/(dashboard)/projects/[projectId]/specs/[specId]/page.tsx`

Spec viewer page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { SpecViewer } from "@/components/specs/SpecViewer"
import { PropertyExtractor } from "@/components/specs/PropertyExtractor"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function SpecDetailPage({ 
  params 
}: { 
  params: { projectId: string; specId: string } 
}) {
  const { data: spec, isLoading } = useQuery({
    queryKey: ["spec", params.specId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/specs/${params.specId}`)
      return res.json()
    },
  })

  const { data: properties } = useQuery({
    queryKey: ["spec-properties", params.specId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/specs/${params.specId}/properties`)
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">{spec?.spec_name}</h1>
          <p className="text-muted-foreground">Specification viewer</p>
        </div>

        <Tabs defaultValue="spec" className="w-full">
          <TabsList>
            <TabsTrigger value="spec">Spec</TabsTrigger>
            <TabsTrigger value="properties">Properties</TabsTrigger>
          </TabsList>

          <TabsContent value="spec">
            <SpecViewer
              specId={params.specId}
              requirements={spec?.requirements}
              design={spec?.design}
              tasks={spec?.tasks}
            />
          </TabsContent>

          <TabsContent value="properties">
            <PropertyExtractor specId={params.specId} properties={properties || []} />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}
```

---

## 18. Validation Review Page

### `app/(dashboard)/tasks/[taskId]/validation/page.tsx`

Validation review page for validator agents.

```tsx
"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ValidationReviewPanel } from "@/components/validation/ValidationReviewPanel"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { useToast } from "@/hooks/use-toast"

export default function ValidationReviewPage({ 
  params 
}: { 
  params: { taskId: string } 
}) {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: task } = useQuery({
    queryKey: ["task", params.taskId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/tasks/${params.taskId}`)
      return res.json()
    },
  })

  const mutation = useMutation({
    mutationFn: async (review: {
      validation_passed: boolean
      feedback: string
      evidence?: string
      recommendations?: string
    }) => {
      const res = await fetch(`/api/validation/give_review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: params.taskId,
          ...review,
        }),
      })
      return res.json()
    },
    onSuccess: () => {
      toast({ title: "Review submitted successfully" })
      queryClient.invalidateQueries({ queryKey: ["task", params.taskId] })
    },
  })

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Validation Review</h1>
          <p className="text-muted-foreground">Task: {task?.description}</p>
        </div>

        <ValidationReviewPanel taskId={params.taskId} onSubmit={mutation.mutate} />
      </div>
    </DashboardLayout>
  )
}
```

---

## 19. Guardian Intervention Page

### `app/(dashboard)/agents/[agentId]/interventions/page.tsx`

Guardian intervention history page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { InterventionViewer } from "@/components/guardian/InterventionViewer"
import { DashboardLayout } from "@/components/layout/DashboardLayout"

export default function InterventionsPage({ 
  params 
}: { 
  params: { agentId: string } 
}) {
  const { data: interventions, isLoading } = useQuery({
    queryKey: ["interventions", params.agentId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/agents/${params.agentId}/interventions`)
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Guardian Interventions</h1>
          <p className="text-muted-foreground">Agent: {params.agentId}</p>
        </div>

        <InterventionViewer interventions={interventions || []} />
      </div>
    </DashboardLayout>
  )
}
```

---

## 20. Discovery Tracking Page

### `app/(dashboard)/projects/[projectId]/discoveries/page.tsx`

Agent discoveries and workflow branching page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { DiscoveryViewer } from "@/components/discovery/DiscoveryViewer"
import { DashboardLayout } from "@/components/layout/DashboardLayout"

export default function DiscoveriesPage({ 
  params 
}: { 
  params: { projectId: string } 
}) {
  const { data: discoveries, isLoading } = useQuery({
    queryKey: ["discoveries", params.projectId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/projects/${params.projectId}/discoveries`)
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Agent Discoveries</h1>
          <p className="text-muted-foreground">Workflow branching and discoveries</p>
        </div>

        <DiscoveryViewer discoveries={discoveries || []} />
      </div>
    </DashboardLayout>
  )
}
```

---

## 21. Time Tracking Page

### `app/(dashboard)/projects/[projectId]/time/page.tsx`

Time tracking and analytics page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { TimeChart } from "@/components/time/TimeChart"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function TimeTrackingPage({ 
  params 
}: { 
  params: { projectId: string } 
}) {
  const { data: timeData, isLoading } = useQuery({
    queryKey: ["time-tracking", params.projectId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/projects/${params.projectId}/time`)
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Time Tracking</h1>
          <p className="text-muted-foreground">Time analytics and breakdown</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Total Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timeData?.total_hours || 0}h</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>This Week</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timeData?.week_hours || 0}h</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Average per Task</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{timeData?.avg_hours || 0}h</div>
            </CardContent>
          </Card>
        </div>

        <TimeChart projectId={params.projectId} />
      </div>
    </DashboardLayout>
  )
}
```

---

## 22. Help Center Page

### `app/(dashboard)/help/page.tsx`

Help center page.

```tsx
"use client"

import { HelpCenter } from "@/components/help/HelpCenter"
import { DashboardLayout } from "@/components/layout/DashboardLayout"

export default function HelpPage() {
  return (
    <DashboardLayout>
      <HelpCenter />
    </DashboardLayout>
  )
}
```

---

## 23. Templates Page

### `app/(dashboard)/templates/page.tsx`

Template library page.

```tsx
"use client"

import { useQuery } from "@tanstack/react-query"
import { TemplateSelector } from "@/components/templates/TemplateSelector"
import { DashboardLayout } from "@/components/layout/DashboardLayout"

export default function TemplatesPage() {
  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: async () => {
      const res = await fetch("/api/v1/templates")
      return res.json()
    },
  })

  if (isLoading) return <div>Loading...</div>

  const handleSelect = (template: any) => {
    // Navigate to create page with template
    window.location.href = `/tickets/create?template=${template.id}`
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Templates</h1>
          <p className="text-muted-foreground">Select a template to get started</p>
        </div>

        <TemplateSelector templates={templates || []} onSelect={handleSelect} />
      </div>
    </DashboardLayout>
  )
}
```

---

This completes all missing pages for the scaffold documentation.
