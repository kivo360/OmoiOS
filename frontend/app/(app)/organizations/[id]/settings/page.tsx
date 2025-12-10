"use client"

import { use, useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
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
  Shield,
  Trash2,
  AlertTriangle,
  AlertCircle,
} from "lucide-react"
import { useOrganization, useUpdateOrganization, useDeleteOrganization, useMembers } from "@/hooks/useOrganizations"
import { useProjects } from "@/hooks/useProjects"

interface OrganizationSettingsPageProps {
  params: Promise<{ id: string }>
}

export default function OrganizationSettingsPage({ params }: OrganizationSettingsPageProps) {
  const { id } = use(params)
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    description: "",
  })
  const [settings, setSettings] = useState({
    allowMemberInvites: true,
    requireApproval: false,
  })

  const { data: org, isLoading: orgLoading, error: orgError } = useOrganization(id)
  const { data: members } = useMembers(id)
  const { data: projects } = useProjects()
  const updateMutation = useUpdateOrganization()
  const deleteMutation = useDeleteOrganization()

  // Populate form when org loads
  useEffect(() => {
    if (org) {
      setFormData({
        name: org.name || "",
        slug: org.slug || "",
        description: org.description || "",
      })
    }
  }, [org])

  const memberCount = members?.length || 0
  // Note: Projects don't have organization_id in the current API response
  // For now, we just show the total count from members in this org
  const projectCount = projects?.total || 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await updateMutation.mutateAsync({
        orgId: id,
        data: {
          name: formData.name,
          description: formData.description || undefined,
        },
      })
      toast.success("Organization settings updated")
    } catch (err) {
      toast.error("Failed to update organization")
    }
  }

  const handleDeleteOrganization = async () => {
    try {
      await deleteMutation.mutateAsync(id)
      toast.success("Organization deleted")
      router.push("/organizations")
    } catch (err) {
      toast.error("Failed to delete organization")
    }
  }

  if (orgLoading) {
    return (
      <div className="container mx-auto max-w-3xl p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-20 w-20 rounded-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (orgError || !org) {
    return (
      <div className="container mx-auto max-w-3xl p-6">
        <Card className="border-destructive/50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-destructive/50" />
            <h3 className="mt-4 text-lg font-semibold">Failed to load organization</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              The organization may not exist or you don&apos;t have access.
            </p>
            <Button variant="outline" className="mt-4" asChild>
              <Link href="/organizations">Back to Organizations</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
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
                <Label>Slug</Label>
                <div className="flex items-center h-10 px-3 rounded-md border bg-muted text-sm text-muted-foreground">
                  {org.slug}
                </div>
                <p className="text-xs text-muted-foreground">
                  Slug cannot be changed after creation
                </p>
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

            <p className="text-xs text-muted-foreground">
              Note: These settings are stored locally. Backend support coming soon.
            </p>
          </CardContent>
        </Card>

        {/* Usage Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Usage Summary</CardTitle>
            <CardDescription>Current organization resources</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">Members</p>
                <p className="text-2xl font-bold">{memberCount}</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">Projects</p>
                <p className="text-2xl font-bold">{projectCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
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
                <Button variant="destructive" disabled={deleteMutation.isPending}>
                  {deleteMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="mr-2 h-4 w-4" />
                  )}
                  Delete Organization
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete the
                    organization <strong>{org.name}</strong> and remove all associated
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
