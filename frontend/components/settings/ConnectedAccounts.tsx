"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Github, Mail, GitlabIcon, Loader2, Check, Link2, Link2Off, ExternalLink } from "lucide-react"
import {
  getOAuthProviders,
  getConnectedProviders,
  disconnectProvider,
  startOAuthFlow,
} from "@/lib/api/oauth"
import type { OAuthProvider, ConnectedProvider } from "@/lib/api/types"

interface ProviderConfig {
  name: string
  icon: React.ComponentType<{ className?: string }>
  description: string
  scopes: string[]
}

const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  github: {
    name: "GitHub",
    icon: Github,
    description: "Connect GitHub for repository access and code management",
    scopes: ["Profile", "Email", "Repositories", "Organizations"],
  },
  google: {
    name: "Google",
    icon: Mail,
    description: "Sign in with your Google account",
    scopes: ["Profile", "Email"],
  },
  gitlab: {
    name: "GitLab",
    icon: GitlabIcon,
    description: "Connect GitLab for repository access",
    scopes: ["Profile", "Email"],
  },
}

export function ConnectedAccounts() {
  const [availableProviders, setAvailableProviders] = useState<OAuthProvider[]>([])
  const [connectedProviders, setConnectedProviders] = useState<ConnectedProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)

  // Fetch providers on mount
  useEffect(() => {
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    try {
      setLoading(true)
      const [available, connected] = await Promise.all([
        getOAuthProviders(),
        getConnectedProviders().catch(() => ({ providers: [] })),
      ])
      setAvailableProviders(available.providers)
      setConnectedProviders(connected.providers)
    } catch (error) {
      console.error("Failed to fetch providers:", error)
      toast.error("Failed to load connected accounts")
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (provider: string) => {
    setConnecting(provider)
    try {
      // Redirect to OAuth flow
      startOAuthFlow(provider)
    } catch (error) {
      console.error("Failed to start OAuth flow:", error)
      toast.error(`Failed to connect ${PROVIDER_CONFIGS[provider]?.name || provider}`)
      setConnecting(null)
    }
  }

  const handleDisconnect = async (provider: string) => {
    setDisconnecting(provider)
    try {
      await disconnectProvider(provider)
      setConnectedProviders((prev) => prev.filter((p) => p.provider !== provider))
      toast.success(`${PROVIDER_CONFIGS[provider]?.name || provider} disconnected`)
    } catch (error: any) {
      console.error("Failed to disconnect provider:", error)
      toast.error(error?.message || `Failed to disconnect ${PROVIDER_CONFIGS[provider]?.name || provider}`)
    } finally {
      setDisconnecting(null)
    }
  }

  const isConnected = (provider: string) => {
    return connectedProviders.some((p) => p.provider === provider)
  }

  const getConnectedInfo = (provider: string) => {
    return connectedProviders.find((p) => p.provider === provider)
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Connected Accounts</CardTitle>
          <CardDescription>Manage your connected OAuth providers</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-48" />
                </div>
              </div>
              <Skeleton className="h-9 w-24" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Connected Accounts</CardTitle>
        <CardDescription>
          Connect third-party accounts to enable additional features like repository access
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {availableProviders.map((provider) => {
          const config = PROVIDER_CONFIGS[provider.name] || {
            name: provider.name,
            icon: Link2,
            description: `Connect your ${provider.name} account`,
            scopes: [],
          }
          const connected = isConnected(provider.name)
          const connectedInfo = getConnectedInfo(provider.name)
          const Icon = config.icon
          const isLoading = connecting === provider.name || disconnecting === provider.name

          return (
            <div
              key={provider.name}
              className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                connected ? "border-primary/30 bg-primary/5" : ""
              } ${!provider.enabled ? "opacity-60" : ""}`}
            >
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    connected ? "bg-primary/20" : "bg-muted"
                  }`}
                >
                  <Icon className={`h-5 w-5 ${connected ? "text-primary" : "text-muted-foreground"}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{config.name}</span>
                    {connected && (
                      <Badge variant="default" className="text-xs">
                        <Check className="mr-1 h-3 w-3" />
                        Connected
                      </Badge>
                    )}
                    {!provider.enabled && (
                      <Badge variant="secondary" className="text-xs">
                        Not configured
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {connected && connectedInfo?.username
                      ? `Connected as @${connectedInfo.username}`
                      : config.description}
                  </p>
                  {!connected && config.scopes.length > 0 && (
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {config.scopes.map((scope) => (
                        <Badge key={scope} variant="outline" className="text-xs">
                          {scope}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {connected ? (
                  <>
                    {provider.name === "github" && (
                      <Button variant="outline" size="sm" asChild>
                        <a
                          href="https://github.com/settings/connections/applications"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Manage
                        </a>
                      </Button>
                    )}
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm" disabled={isLoading}>
                          {disconnecting === provider.name ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <Link2Off className="mr-2 h-4 w-4" />
                          )}
                          Disconnect
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Disconnect {config.name}?</AlertDialogTitle>
                          <AlertDialogDescription>
                            You will no longer be able to access {config.name} features like repository
                            management. You can reconnect at any time.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDisconnect(provider.name)}>
                            Disconnect
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </>
                ) : (
                  <Button
                    size="sm"
                    disabled={!provider.enabled || isLoading}
                    onClick={() => handleConnect(provider.name)}
                  >
                    {connecting === provider.name ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Link2 className="mr-2 h-4 w-4" />
                    )}
                    Connect
                  </Button>
                )}
              </div>
            </div>
          )
        })}

        {availableProviders.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No OAuth providers are configured. Contact your administrator to enable OAuth authentication.
          </div>
        )}
      </CardContent>
    </Card>
  )
}
