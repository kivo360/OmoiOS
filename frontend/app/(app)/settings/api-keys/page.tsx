"use client"

import { useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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
import { ArrowLeft, Plus, Key, Copy, Trash2, Clock, AlertCircle, Loader2 } from "lucide-react"
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "@/hooks/useApiKeys"

export default function ApiKeysPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState("")
  const [showNewKey, setShowNewKey] = useState<string | null>(null)

  const { data: apiKeys, isLoading, error } = useApiKeys()
  const createMutation = useCreateApiKey()
  const revokeMutation = useRevokeApiKey()

  const handleCreateKey = async () => {
    try {
      const result = await createMutation.mutateAsync({ name: newKeyName })
      setShowNewKey(result.key)
      setNewKeyName("")
      setIsDialogOpen(false)
      toast.success("API key created successfully!")
    } catch (err) {
      toast.error("Failed to create API key")
    }
  }

  const handleDeleteKey = async (keyId: string) => {
    try {
      await revokeMutation.mutateAsync(keyId)
      toast.success("API key revoked")
    } catch (err) {
      toast.error("Failed to revoke API key")
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Copied to clipboard")
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never"
    return new Date(dateStr).toLocaleDateString("en-US", { 
      month: "short", 
      day: "numeric", 
      year: "numeric" 
    })
  }

  const formatTimeAgo = (dateStr: string | null) => {
    if (!dateStr) return "Never"
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  return (
    <div className="container mx-auto max-w-3xl p-6 space-y-6">
      <Link
        href="/settings"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Settings
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">API Keys</h1>
          <p className="text-muted-foreground">
            Manage API keys for programmatic access
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Create Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Create a new API key for accessing the OmoiOS API.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="keyName">Key Name</Label>
                <Input
                  id="keyName"
                  placeholder="e.g., Production API"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button 
                onClick={handleCreateKey} 
                disabled={!newKeyName || createMutation.isPending}
              >
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {createMutation.isPending ? "Creating..." : "Create Key"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* New Key Display */}
      {showNewKey && (
        <Card className="border-success bg-success/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-success">API key created!</p>
                <p className="text-sm text-muted-foreground">
                  Copy this key now. You won&apos;t be able to see it again.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => copyToClipboard(showNewKey)}>
                <Copy className="mr-2 h-4 w-4" /> Copy
              </Button>
            </div>
            <code className="mt-2 block rounded bg-muted p-2 text-sm font-mono">
              {showNewKey}
            </code>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => setShowNewKey(null)}
            >
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive/50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-destructive/50" />
            <h3 className="mt-4 text-lg font-semibold">Failed to load API keys</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Please try refreshing the page.
            </p>
          </CardContent>
        </Card>
      )}

      {/* API Keys List */}
      {!isLoading && !error && (
        <div className="space-y-4">
          {apiKeys?.map((key) => (
            <Card key={key.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <Key className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{key.name}</p>
                        <Badge variant={key.is_active ? "default" : "secondary"}>
                          {key.is_active ? "active" : "inactive"}
                        </Badge>
                      </div>
                      <code className="text-sm text-muted-foreground">{key.key_prefix}****</code>
                    </div>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="text-destructive"
                        disabled={revokeMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to revoke &quot;{key.name}&quot;? This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => handleDeleteKey(key.id)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Revoke
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
                <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Last used: {formatTimeAgo(key.last_used_at)}
                  </span>
                  <span>Created: {formatDate(key.created_at)}</span>
                  {key.expires_at && (
                    <span>Expires: {formatDate(key.expires_at)}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && !error && apiKeys?.length === 0 && (
        <Card className="p-12 text-center">
          <Key className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No API keys</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Create an API key to get started with the OmoiOS API.
          </p>
        </Card>
      )}
    </div>
  )
}
