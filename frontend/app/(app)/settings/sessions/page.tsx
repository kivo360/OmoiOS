"use client"

import { useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import {
  ArrowLeft,
  Monitor,
  Smartphone,
  Tablet,
  Globe,
  LogOut,
  Search,
  RefreshCw,
  Shield,
  MapPin,
  Clock,
  Calendar,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Mock session data
const mockSessions = [
  {
    id: "sess-001",
    device: "Chrome on macOS",
    deviceType: "desktop",
    browser: "Chrome 120",
    os: "macOS Sonoma",
    location: "San Francisco, CA",
    country: "United States",
    ip: "192.168.1.1",
    lastActive: "Active now",
    isCurrent: true,
    createdAt: "Dec 1, 2025, 9:30 AM",
    expiresAt: "Dec 31, 2025",
  },
  {
    id: "sess-002",
    device: "Safari on iPhone",
    deviceType: "mobile",
    browser: "Safari 17",
    os: "iOS 17.2",
    location: "San Francisco, CA",
    country: "United States",
    ip: "192.168.1.2",
    lastActive: "2 hours ago",
    isCurrent: false,
    createdAt: "Nov 28, 2025, 3:45 PM",
    expiresAt: "Dec 28, 2025",
  },
  {
    id: "sess-003",
    device: "Firefox on Windows",
    deviceType: "desktop",
    browser: "Firefox 121",
    os: "Windows 11",
    location: "New York, NY",
    country: "United States",
    ip: "10.0.0.45",
    lastActive: "1 day ago",
    isCurrent: false,
    createdAt: "Nov 25, 2025, 11:20 AM",
    expiresAt: "Dec 25, 2025",
  },
  {
    id: "sess-004",
    device: "Chrome on Android",
    deviceType: "mobile",
    browser: "Chrome 120",
    os: "Android 14",
    location: "Chicago, IL",
    country: "United States",
    ip: "172.16.0.100",
    lastActive: "3 days ago",
    isCurrent: false,
    createdAt: "Nov 20, 2025, 8:15 PM",
    expiresAt: "Dec 20, 2025",
  },
  {
    id: "sess-005",
    device: "Safari on iPad",
    deviceType: "tablet",
    browser: "Safari 17",
    os: "iPadOS 17.2",
    location: "Los Angeles, CA",
    country: "United States",
    ip: "192.168.5.50",
    lastActive: "5 days ago",
    isCurrent: false,
    createdAt: "Nov 15, 2025, 2:00 PM",
    expiresAt: "Dec 15, 2025",
  },
]

export default function SessionsPage() {
  const [sessions, setSessions] = useState(mockSessions)
  const [selectedSession, setSelectedSession] = useState<typeof mockSessions[0] | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [isRefreshing, setIsRefreshing] = useState(false)

  const filteredSessions = sessions.filter(
    (session) =>
      session.device.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.ip.includes(searchQuery)
  )

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 500))
      setSessions(sessions.filter((s) => s.id !== sessionId))
      toast.success("Session revoked successfully")
      setSelectedSession(null)
    } catch {
      toast.error("Failed to revoke session")
    }
  }

  const handleRevokeAllSessions = async () => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 500))
      setSessions(sessions.filter((s) => s.isCurrent))
      toast.success("All other sessions revoked")
    } catch {
      toast.error("Failed to revoke sessions")
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsRefreshing(false)
    toast.success("Sessions refreshed")
  }

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case "mobile":
        return <Smartphone className="h-4 w-4" />
      case "tablet":
        return <Tablet className="h-4 w-4" />
      case "desktop":
        return <Monitor className="h-4 w-4" />
      default:
        return <Globe className="h-4 w-4" />
    }
  }

  const otherSessionCount = sessions.filter((s) => !s.isCurrent).length

  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-6">
      <Link
        href="/settings"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Settings
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Active Sessions</h1>
          <p className="text-muted-foreground">
            Manage your active login sessions across all devices
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", isRefreshing && "animate-spin")} />
            Refresh
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="destructive"
                size="sm"
                disabled={otherSessionCount === 0}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Revoke All ({otherSessionCount})
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Revoke All Other Sessions?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will sign out {otherSessionCount} session(s) on all other devices.
                  You will remain signed in on this device.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleRevokeAllSessions}>
                  Revoke All
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Current Session Card */}
      {sessions.find((s) => s.isCurrent) && (
        <Card className="border-primary/50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Current Session</CardTitle>
              <Badge variant="default" className="ml-auto">Active</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {(() => {
              const current = sessions.find((s) => s.isCurrent)!
              return (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="flex items-center gap-3">
                    {getDeviceIcon(current.deviceType)}
                    <div>
                      <p className="font-medium">{current.device}</p>
                      <p className="text-xs text-muted-foreground">{current.browser}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{current.location}</p>
                      <p className="text-xs text-muted-foreground font-mono">{current.ip}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Signed in</p>
                      <p className="text-xs text-muted-foreground">{current.createdAt}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Expires</p>
                      <p className="text-xs text-muted-foreground">{current.expiresAt}</p>
                    </div>
                  </div>
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}

      {/* Other Sessions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Other Sessions</CardTitle>
              <CardDescription>
                {otherSessionCount === 0
                  ? "No other active sessions"
                  : `${otherSessionCount} other active session${otherSessionCount > 1 ? "s" : ""}`}
              </CardDescription>
            </div>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredSessions.filter((s) => !s.isCurrent).length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? "No sessions match your search" : "No other active sessions"}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Last Active</TableHead>
                  <TableHead>Signed In</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSessions
                  .filter((s) => !s.isCurrent)
                  .map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                            {getDeviceIcon(session.deviceType)}
                          </div>
                          <div>
                            <p className="font-medium">{session.device}</p>
                            <p className="text-xs text-muted-foreground">
                              {session.browser} • {session.os}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p>{session.location}</p>
                          <p className="text-xs text-muted-foreground font-mono">
                            {session.ip}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-muted-foreground">{session.lastActive}</span>
                      </TableCell>
                      <TableCell>
                        <span className="text-muted-foreground text-sm">
                          {session.createdAt.split(",")[0]}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedSession(session)}
                          >
                            Details
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                              >
                                Revoke
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Revoke Session?</AlertDialogTitle>
                                <AlertDialogDescription>
                                  This will sign out the session on {session.device} in{" "}
                                  {session.location}. The user will need to sign in again.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => handleRevokeSession(session.id)}
                                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                  Revoke Session
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Security Tips */}
      <Card className="bg-muted/30">
        <CardHeader>
          <CardTitle className="text-base">Security Tips</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            • <strong>Unrecognized sessions?</strong> If you see a session you don't recognize,
            revoke it immediately and change your password.
          </p>
          <p>
            • <strong>Keep sessions minimal.</strong> Regularly review and revoke sessions you
            no longer need.
          </p>
          <p>
            • <strong>Enable 2FA.</strong> Two-factor authentication adds an extra layer of
            security to your account.{" "}
            <Link href="/settings/security" className="text-primary hover:underline">
              Enable in Security Settings →
            </Link>
          </p>
        </CardContent>
      </Card>

      {/* Session Detail Dialog */}
      <Dialog open={!!selectedSession} onOpenChange={() => setSelectedSession(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Session Details</DialogTitle>
            <DialogDescription>
              Full information about this login session
            </DialogDescription>
          </DialogHeader>
          {selectedSession && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-muted">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-background">
                  {getDeviceIcon(selectedSession.deviceType)}
                </div>
                <div>
                  <p className="font-medium">{selectedSession.device}</p>
                  <p className="text-sm text-muted-foreground">{selectedSession.os}</p>
                </div>
              </div>
              <Separator />
              <div className="grid gap-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Browser</span>
                  <span className="font-medium">{selectedSession.browser}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Location</span>
                  <span className="font-medium">{selectedSession.location}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Country</span>
                  <span className="font-medium">{selectedSession.country}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IP Address</span>
                  <span className="font-mono">{selectedSession.ip}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Active</span>
                  <span>{selectedSession.lastActive}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Signed In</span>
                  <span>{selectedSession.createdAt}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Expires</span>
                  <span>{selectedSession.expiresAt}</span>
                </div>
              </div>
            </div>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setSelectedSession(null)}>
              Close
            </Button>
            {selectedSession && !selectedSession.isCurrent && (
              <Button
                variant="destructive"
                onClick={() => handleRevokeSession(selectedSession.id)}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Revoke Session
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
