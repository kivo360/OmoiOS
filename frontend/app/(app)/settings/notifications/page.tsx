"use client"

import { useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ArrowLeft,
  Loader2,
  Shield,
  Bell,
  Mail,
  MessageSquare,
  Slack,
  Bot,
  CheckCircle2,
  AlertCircle,
  Workflow,
  GitBranch,
} from "lucide-react"

interface NotificationSetting {
  id: string
  label: string
  description: string
  icon: React.ElementType
  inApp: boolean
  email: boolean
  slack: boolean
}

export default function NotificationsSettingsPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [digestFrequency, setDigestFrequency] = useState("daily")
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false)
  const [quietHoursStart, setQuietHoursStart] = useState("22:00")
  const [quietHoursEnd, setQuietHoursEnd] = useState("08:00")
  
  const [notifications, setNotifications] = useState<NotificationSetting[]>([
    {
      id: "agent_complete",
      label: "Agent Completions",
      description: "When an agent successfully completes a task",
      icon: CheckCircle2,
      inApp: true,
      email: true,
      slack: true,
    },
    {
      id: "agent_error",
      label: "Agent Errors",
      description: "When an agent encounters an error or failure",
      icon: AlertCircle,
      inApp: true,
      email: true,
      slack: true,
    },
    {
      id: "agent_spawn",
      label: "Agent Spawned",
      description: "When new agents are spawned for tasks",
      icon: Bot,
      inApp: true,
      email: false,
      slack: false,
    },
    {
      id: "phase_transition",
      label: "Phase Transitions",
      description: "When tickets move between phases",
      icon: Workflow,
      inApp: true,
      email: false,
      slack: true,
    },
    {
      id: "gate_approval",
      label: "Gate Approval Required",
      description: "When a phase gate requires your approval",
      icon: Shield,
      inApp: true,
      email: true,
      slack: true,
    },
    {
      id: "pr_created",
      label: "Pull Request Created",
      description: "When agents create pull requests",
      icon: GitBranch,
      inApp: true,
      email: true,
      slack: true,
    },
    {
      id: "mentions",
      label: "Mentions & Comments",
      description: "When someone mentions you in comments",
      icon: MessageSquare,
      inApp: true,
      email: true,
      slack: false,
    },
  ])

  const handleToggle = (id: string, channel: "inApp" | "email" | "slack") => {
    setNotifications(
      notifications.map((n) =>
        n.id === id ? { ...n, [channel]: !n[channel] } : n
      )
    )
  }

  const handleSave = async () => {
    setIsLoading(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      toast.success("Notification preferences saved!")
    } catch {
      toast.error("Failed to save preferences")
    } finally {
      setIsLoading(false)
    }
  }

  const handleEnableAll = (channel: "inApp" | "email" | "slack") => {
    setNotifications(notifications.map((n) => ({ ...n, [channel]: true })))
  }

  const handleDisableAll = (channel: "inApp" | "email" | "slack") => {
    setNotifications(notifications.map((n) => ({ ...n, [channel]: false })))
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
        <h1 className="text-2xl font-bold">Notification Settings</h1>
        <p className="text-muted-foreground">Configure how you receive notifications</p>
      </div>

      <div className="space-y-6">
          {/* Notification Channels Card */}
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Choose how you want to be notified for different events
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Channel Headers */}
              <div className="flex items-center justify-end gap-4 mb-4 pr-2">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Bell className="h-3 w-3" />
                  <span>In-App</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Mail className="h-3 w-3" />
                  <span>Email</span>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Slack className="h-3 w-3" />
                  <span>Slack</span>
                </div>
              </div>

              <div className="space-y-4">
                {notifications.map((notification, index) => (
                  <div key={notification.id}>
                    {index > 0 && <Separator className="mb-4" />}
                    <div className="flex items-center justify-between">
                      <div className="flex items-start gap-3">
                        <notification.icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
                        <div>
                          <Label className="font-medium">{notification.label}</Label>
                          <p className="text-sm text-muted-foreground">
                            {notification.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <Switch
                          checked={notification.inApp}
                          onCheckedChange={() => handleToggle(notification.id, "inApp")}
                        />
                        <Switch
                          checked={notification.email}
                          onCheckedChange={() => handleToggle(notification.id, "email")}
                        />
                        <Switch
                          checked={notification.slack}
                          onCheckedChange={() => handleToggle(notification.id, "slack")}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Bulk Actions */}
              <div className="mt-6 pt-4 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Bulk Actions</span>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleEnableAll("inApp")}>
                      Enable All In-App
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleEnableAll("email")}>
                      Enable All Email
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDisableAll("email")}>
                      Disable All Email
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Email Digest Card */}
          <Card>
            <CardHeader>
              <CardTitle>Email Digest</CardTitle>
              <CardDescription>
                Receive a summary of activity instead of individual emails
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Digest Frequency</Label>
                  <p className="text-sm text-muted-foreground">
                    How often to receive digest emails
                  </p>
                </div>
                <Select value={digestFrequency} onValueChange={setDigestFrequency}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="realtime">Real-time</SelectItem>
                    <SelectItem value="hourly">Hourly</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="never">Never</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {digestFrequency === "daily" && (
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-sm text-muted-foreground">
                    Daily digest will be sent at 9:00 AM in your timezone
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quiet Hours Card */}
          <Card>
            <CardHeader>
              <CardTitle>Quiet Hours</CardTitle>
              <CardDescription>
                Pause notifications during specific hours
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Enable Quiet Hours</Label>
                  <p className="text-sm text-muted-foreground">
                    Pause push and in-app notifications
                  </p>
                </div>
                <Switch
                  checked={quietHoursEnabled}
                  onCheckedChange={setQuietHoursEnabled}
                />
              </div>
              {quietHoursEnabled && (
                <div className="grid gap-4 sm:grid-cols-2 pt-2">
                  <div className="space-y-2">
                    <Label htmlFor="quietStart">Start Time</Label>
                    <Select value={quietHoursStart} onValueChange={setQuietHoursStart}>
                      <SelectTrigger id="quietStart">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 24 }, (_, i) => {
                          const hour = i.toString().padStart(2, "0")
                          return (
                            <SelectItem key={hour} value={`${hour}:00`}>
                              {`${hour}:00`}
                            </SelectItem>
                          )
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="quietEnd">End Time</Label>
                    <Select value={quietHoursEnd} onValueChange={setQuietHoursEnd}>
                      <SelectTrigger id="quietEnd">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 24 }, (_, i) => {
                          const hour = i.toString().padStart(2, "0")
                          return (
                            <SelectItem key={hour} value={`${hour}:00`}>
                              {`${hour}:00`}
                            </SelectItem>
                          )
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Slack Integration Card */}
          <Card>
            <CardHeader>
              <CardTitle>Slack Integration</CardTitle>
              <CardDescription>
                Connect Slack to receive notifications in your workspace
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#4A154B]/10">
                    <Slack className="h-5 w-5 text-[#4A154B]" />
                  </div>
                  <div>
                    <p className="font-medium">Slack Workspace</p>
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  </div>
                </div>
                <Button variant="outline">
                  Connect Slack
                </Button>
              </div>
            </CardContent>
          </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  )
}
