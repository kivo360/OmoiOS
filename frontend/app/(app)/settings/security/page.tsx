"use client"

import { useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
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
  Loader2,
  Shield,
  Monitor,
  Smartphone,
  Globe,
  LogOut,
  Trash2,
  Eye,
  EyeOff,
  Check,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Mock session data
const mockSessions = [
  {
    id: "sess-001",
    device: "Chrome on macOS",
    deviceType: "desktop",
    location: "San Francisco, CA",
    ip: "192.168.1.1",
    lastActive: "Active now",
    isCurrent: true,
    createdAt: "Dec 1, 2025",
  },
  {
    id: "sess-002",
    device: "Safari on iPhone",
    deviceType: "mobile",
    location: "San Francisco, CA",
    ip: "192.168.1.2",
    lastActive: "2 hours ago",
    isCurrent: false,
    createdAt: "Nov 28, 2025",
  },
  {
    id: "sess-003",
    device: "Firefox on Windows",
    deviceType: "desktop",
    location: "New York, NY",
    ip: "10.0.0.45",
    lastActive: "1 day ago",
    isCurrent: false,
    createdAt: "Nov 25, 2025",
  },
  {
    id: "sess-004",
    device: "Chrome on Android",
    deviceType: "mobile",
    location: "Chicago, IL",
    ip: "172.16.0.100",
    lastActive: "3 days ago",
    isCurrent: false,
    createdAt: "Nov 20, 2025",
  },
]

export default function SecuritySettingsPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [sessions, setSessions] = useState(mockSessions)
  const [selectedSession, setSelectedSession] = useState<typeof mockSessions[0] | null>(null)
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  })
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false)

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error("Passwords do not match")
      return
    }
    setIsLoading(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      toast.success("Password updated successfully!")
      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
    } catch {
      toast.error("Failed to update password")
    } finally {
      setIsLoading(false)
    }
  }

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

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case "mobile":
        return <Smartphone className="h-4 w-4" />
      case "desktop":
        return <Monitor className="h-4 w-4" />
      default:
        return <Globe className="h-4 w-4" />
    }
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

      <div>
        <h1 className="text-2xl font-bold">Security Settings</h1>
        <p className="text-muted-foreground">Manage your account security and active sessions</p>
      </div>

      <div className="space-y-6">
          {/* Password Change Card */}
          <Card>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>Update your account password</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="currentPassword"
                      type={showCurrentPassword ? "text" : "password"}
                      value={passwordForm.currentPassword}
                      onChange={(e) =>
                        setPasswordForm({ ...passwordForm, currentPassword: e.target.value })
                      }
                      placeholder="Enter current password"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    >
                      {showCurrentPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="newPassword">New Password</Label>
                    <div className="relative">
                      <Input
                        id="newPassword"
                        type={showNewPassword ? "text" : "password"}
                        value={passwordForm.newPassword}
                        onChange={(e) =>
                          setPasswordForm({ ...passwordForm, newPassword: e.target.value })
                        }
                        placeholder="Enter new password"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                      >
                        {showNewPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm New Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={passwordForm.confirmPassword}
                      onChange={(e) =>
                        setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })
                      }
                      placeholder="Confirm new password"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={isLoading}>
                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Update Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Two-Factor Authentication Card */}
          <Card>
            <CardHeader>
              <CardTitle>Two-Factor Authentication</CardTitle>
              <CardDescription>Add an extra layer of security to your account</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">
                      {twoFactorEnabled ? "2FA is enabled" : "2FA is disabled"}
                    </span>
                    {twoFactorEnabled && (
                      <Badge variant="default" className="text-xs">
                        <Check className="mr-1 h-3 w-3" />
                        Active
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {twoFactorEnabled
                      ? "Your account is protected with two-factor authentication"
                      : "Protect your account with a secondary authentication method"}
                  </p>
                </div>
                <Switch
                  checked={twoFactorEnabled}
                  onCheckedChange={setTwoFactorEnabled}
                />
              </div>
              {!twoFactorEnabled && (
                <div className="mt-4 rounded-lg bg-muted p-4">
                  <p className="text-sm text-muted-foreground">
                    Enable two-factor authentication to require a verification code in addition
                    to your password when signing in.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active Sessions Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Active Sessions</CardTitle>
                <CardDescription>Manage your logged-in devices</CardDescription>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" disabled={sessions.length <= 1}>
                    <LogOut className="mr-2 h-4 w-4" />
                    Revoke All Others
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Revoke All Other Sessions?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will sign out all devices except your current session. You will need
                      to sign in again on those devices.
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
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Last Active</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getDeviceIcon(session.deviceType)}
                          <div>
                            <p className="font-medium">{session.device}</p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {session.ip}
                            </p>
                          </div>
                          {session.isCurrent && (
                            <Badge variant="secondary" className="text-xs">
                              Current
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{session.location}</TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            session.isCurrent && "text-green-600 font-medium"
                          )}
                        >
                          {session.lastActive}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedSession(session)}
                          >
                            View
                          </Button>
                          {!session.isCurrent && (
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
                                    This will sign out the session on {session.device}. The
                                    user will need to sign in again.
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
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

        {/* Danger Zone Card */}
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>Irreversible actions for your account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <p className="font-medium">Delete Account</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete your account and all associated data
                </p>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete Account
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This action cannot be undone. This will permanently delete your account
                      and remove all associated data from our servers.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                      Delete Account
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Session Detail Dialog */}
      <Dialog open={!!selectedSession} onOpenChange={() => setSelectedSession(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Session Details</DialogTitle>
            <DialogDescription>
              Information about this login session
            </DialogDescription>
          </DialogHeader>
          {selectedSession && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {getDeviceIcon(selectedSession.deviceType)}
                <div>
                  <p className="font-medium">{selectedSession.device}</p>
                  {selectedSession.isCurrent && (
                    <Badge variant="default" className="text-xs mt-1">
                      Current Session
                    </Badge>
                  )}
                </div>
              </div>
              <Separator />
              <div className="grid gap-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Location</span>
                  <span>{selectedSession.location}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IP Address</span>
                  <span className="font-mono">{selectedSession.ip}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Active</span>
                  <span>{selectedSession.lastActive}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Signed In</span>
                  <span>{selectedSession.createdAt}</span>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedSession(null)}>
              Close
            </Button>
            {selectedSession && !selectedSession.isCurrent && (
              <Button
                variant="destructive"
                onClick={() => handleRevokeSession(selectedSession.id)}
              >
                Revoke Session
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
