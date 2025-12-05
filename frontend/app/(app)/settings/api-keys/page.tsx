"use client"

import { useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
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
import { ArrowLeft, Plus, Key, Copy, Trash2, Eye, EyeOff, Clock } from "lucide-react"

// Mock API keys
const mockApiKeys = [
  {
    id: "key-001",
    name: "Production API",
    prefix: "sk_prod_****",
    lastUsed: "2 hours ago",
    createdAt: "Jan 15, 2024",
    status: "active",
  },
  {
    id: "key-002",
    name: "Development API",
    prefix: "sk_dev_****",
    lastUsed: "1 day ago",
    createdAt: "Jan 10, 2024",
    status: "active",
  },
  {
    id: "key-003",
    name: "CI/CD Pipeline",
    prefix: "sk_ci_****",
    lastUsed: "Never",
    createdAt: "Jan 5, 2024",
    status: "inactive",
  },
]

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState(mockApiKeys)
  const [isCreating, setIsCreating] = useState(false)
  const [newKeyName, setNewKeyName] = useState("")
  const [showNewKey, setShowNewKey] = useState<string | null>(null)

  const handleCreateKey = async () => {
    setIsCreating(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      const newKey = {
        id: `key-${Date.now()}`,
        name: newKeyName,
        prefix: "sk_new_****",
        lastUsed: "Never",
        createdAt: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        status: "active" as const,
      }
      setApiKeys([newKey, ...apiKeys])
      setShowNewKey("sk_new_" + Math.random().toString(36).substring(2, 15))
      setNewKeyName("")
      toast.success("API key created successfully!")
    } catch (error) {
      toast.error("Failed to create API key")
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteKey = (keyId: string) => {
    setApiKeys(apiKeys.filter((k) => k.id !== keyId))
    toast.success("API key deleted")
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Copied to clipboard")
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
        <Dialog>
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
              <Button onClick={handleCreateKey} disabled={!newKeyName || isCreating}>
                {isCreating ? "Creating..." : "Create Key"}
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

      {/* API Keys List */}
      <div className="space-y-4">
        {apiKeys.map((key) => (
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
                      <Badge variant={key.status === "active" ? "default" : "secondary"}>
                        {key.status}
                      </Badge>
                    </div>
                    <code className="text-sm text-muted-foreground">{key.prefix}</code>
                  </div>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete &quot;{key.name}&quot;? This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => handleDeleteKey(key.id)}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
              <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Last used: {key.lastUsed}
                </span>
                <span>Created: {key.createdAt}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {apiKeys.length === 0 && (
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
