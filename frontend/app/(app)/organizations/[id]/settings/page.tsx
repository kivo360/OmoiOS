"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
  Camera,
  Building2,
  CreditCard,
  Shield,
  Trash2,
  AlertTriangle,
  Check,
  Zap,
} from "lucide-react"

interface OrganizationSettingsPageProps {
  params: Promise<{ id: string }>
}

// Mock organization data
const mockOrg = {
  id: "org-001",
  name: "Acme Inc",
  slug: "acme-inc",
  description: "Building the future of automation",
  avatar: null,
  plan: "pro",
  memberCount: 12,
  projectCount: 5,
  billing: {
    email: "billing@acme.com",
    address: "123 Tech Street, San Francisco, CA 94102",
  },
  limits: {
    maxMembers: 25,
    maxProjects: 20,
    maxAgentsPerProject: 10,
    maxConcurrentAgents: 5,
  },
}

const plans = [
  { id: "free", name: "Free", price: "$0/mo", features: ["5 members", "3 projects", "2 agents/project"] },
  { id: "pro", name: "Pro", price: "$49/mo", features: ["25 members", "20 projects", "10 agents/project"] },
  { id: "enterprise", name: "Enterprise", price: "Custom", features: ["Unlimited members", "Unlimited projects", "Custom limits"] },
]

export default function OrganizationSettingsPage({ params }: OrganizationSettingsPageProps) {
  const { id } = use(params)
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: mockOrg.name,
    slug: mockOrg.slug,
    description: mockOrg.description || "",
    billingEmail: mockOrg.billing.email,
    billingAddress: mockOrg.billing.address,
  })
  const [settings, setSettings] = useState({
    allowMemberInvites: true,
    requireApproval: false,
    defaultMemberRole: "member",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsLoading(false)
    toast.success("Organization settings updated")
  }

  const handleDeleteOrganization = async () => {
    toast.error("Organization deletion is disabled in demo mode")
  }

  return (
    <div className="container mx-auto max-w-3xl p-6 space-y-6">
      <Link
        href={`/organizations/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Organization
      </Link>

      <div>
        <h1 className="text-2xl font-bold">Organization Settings</h1>
        <p className="text-muted-foreground">Manage your organization's profile and preferences</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* General Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              General
            </CardTitle>
            <CardDescription>Basic organization information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Avatar */}
            <div className="flex items-center gap-4">
              <Avatar className="h-20 w-20">
                <AvatarImage src={mockOrg.avatar || undefined} />
                <AvatarFallback className="bg-primary/10 text-primary text-2xl">
                  {formData.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <Button type="button" variant="outline" size="sm">
                  <Camera className="mr-2 h-4 w-4" />
                  Change Logo
                </Button>
                <p className="mt-1 text-xs text-muted-foreground">
                  Recommended: 256x256px PNG or JPG
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Organization Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">URL Slug</Label>
                <div className="flex">
                  <span className="inline-flex items-center rounded-l-md border border-r-0 bg-muted px-3 text-sm text-muted-foreground">
                    omoios.com/
                  </span>
                  <Input
                    id="slug"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                    className="rounded-l-none"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Tell us about your organization..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Billing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Billing
            </CardTitle>
            <CardDescription>Manage billing information and subscription</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <p className="font-medium">Current Plan</p>
                <p className="text-sm text-muted-foreground">
                  {plans.find((p) => p.id === mockOrg.plan)?.name} - {plans.find((p) => p.id === mockOrg.plan)?.price}
                </p>
              </div>
              <Badge variant="default" className="capitalize">
                <Zap className="mr-1 h-3 w-3" />
                {mockOrg.plan}
              </Badge>
            </div>

            <div className="grid gap-3">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className={`flex items-center justify-between rounded-lg border p-4 ${
                    plan.id === mockOrg.plan ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{plan.name}</p>
                      <span className="text-sm text-muted-foreground">{plan.price}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {plan.features.join(" • ")}
                    </p>
                  </div>
                  {plan.id === mockOrg.plan ? (
                    <Badge variant="outline">
                      <Check className="mr-1 h-3 w-3" />
                      Current
                    </Badge>
                  ) : (
                    <Button variant="outline" size="sm" type="button">
                      {plan.id === "enterprise" ? "Contact Sales" : "Upgrade"}
                    </Button>
                  )}
                </div>
              ))}
            </div>

            <Separator />

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="billingEmail">Billing Email</Label>
                <Input
                  id="billingEmail"
                  type="email"
                  value={formData.billingEmail}
                  onChange={(e) => setFormData({ ...formData, billingEmail: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="billingAddress">Billing Address</Label>
                <Input
                  id="billingAddress"
                  value={formData.billingAddress}
                  onChange={(e) => setFormData({ ...formData, billingAddress: e.target.value })}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Member Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Member Settings
            </CardTitle>
            <CardDescription>Configure how members join and interact</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Allow member invites</p>
                <p className="text-sm text-muted-foreground">
                  Members can invite others to join the organization
                </p>
              </div>
              <Switch
                checked={settings.allowMemberInvites}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, allowMemberInvites: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Require approval</p>
                <p className="text-sm text-muted-foreground">
                  New members must be approved by an admin
                </p>
              </div>
              <Switch
                checked={settings.requireApproval}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, requireApproval: checked })
                }
              />
            </div>

            <div className="space-y-2">
              <Label>Default member role</Label>
              <Select
                value={settings.defaultMemberRole}
                onValueChange={(value) =>
                  setSettings({ ...settings, defaultMemberRole: value })
                }
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Usage & Limits */}
        <Card>
          <CardHeader>
            <CardTitle>Usage & Limits</CardTitle>
            <CardDescription>Current usage against your plan limits</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Members</span>
                <span className="text-sm font-medium">
                  {mockOrg.memberCount} / {mockOrg.limits.maxMembers}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${(mockOrg.memberCount / mockOrg.limits.maxMembers) * 100}%` }}
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm">Projects</span>
                <span className="text-sm font-medium">
                  {mockOrg.projectCount} / {mockOrg.limits.maxProjects}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${(mockOrg.projectCount / mockOrg.limits.maxProjects) * 100}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </form>

      {/* Danger Zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Danger Zone
          </CardTitle>
          <CardDescription>
            Irreversible actions that affect your entire organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Delete Organization</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete this organization and all its data
              </p>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Organization
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete the
                    organization <strong>{mockOrg.name}</strong> and remove all associated
                    data including projects, members, and settings.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleDeleteOrganization}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Delete Organization
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
