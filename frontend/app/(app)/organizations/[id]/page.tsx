"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowLeft,
  Settings,
  Users,
  FolderGit2,
  Building2,
  UserPlus,
  MoreHorizontal,
  AlertCircle,
  Bot,
  CreditCard,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useOrganization, useMembers, useRoles } from "@/hooks/useOrganizations"
import { useProjects } from "@/hooks/useProjects"

interface OrganizationPageProps {
  params: Promise<{ id: string }>
}

export default function OrganizationPage({ params }: OrganizationPageProps) {
  const { id } = use(params)
  
  // Fetch organization data from API
  const { data: org, isLoading: orgLoading, error: orgError } = useOrganization(id)
  const { data: members, isLoading: membersLoading } = useMembers(id)
  const { data: projects } = useProjects()
  
  // Loading state
  if (orgLoading) {
    return (
      <div className="container mx-auto max-w-5xl p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-16 w-16 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (orgError) {
    return (
      <div className="container mx-auto max-w-5xl p-6 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
        <h1 className="mt-4 text-2xl font-bold">Failed to load organization</h1>
        <p className="mt-2 text-muted-foreground">
          {orgError instanceof Error ? orgError.message : "An error occurred"}
        </p>
        <Button className="mt-4" asChild>
          <Link href="/organizations">Back to Organizations</Link>
        </Button>
      </div>
    )
  }

  if (!org) {
    return (
      <div className="container mx-auto max-w-5xl p-6 text-center">
        <h1 className="text-2xl font-bold">Organization not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/organizations">Back to Organizations</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-5xl p-6 space-y-6">
      <Link
        href="/organizations"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Organizations
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16">
            <AvatarFallback className="bg-primary/10 text-primary text-xl">
              {org.name.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{org.name}</h1>
              <Badge variant={org.is_active ? "default" : "secondary"}>
                {org.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <p className="text-muted-foreground">@{org.slug}</p>
            {org.description && (
              <p className="mt-1 text-sm text-muted-foreground">{org.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href={`/organizations/${id}/billing`}>
              <CreditCard className="mr-2 h-4 w-4" /> Billing
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/organizations/${id}/settings`}>
              <Settings className="mr-2 h-4 w-4" /> Settings
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{members?.length ?? 0}</p>
                <p className="text-sm text-muted-foreground">Members</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{org.max_concurrent_agents}</p>
                <p className="text-sm text-muted-foreground">Max Agents</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Building2 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{org.max_agent_runtime_hours}h</p>
                <p className="text-sm text-muted-foreground">Max Runtime</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="members" className="space-y-4">
        <TabsList>
          <TabsTrigger value="members">Members ({members?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="projects">Projects ({projects?.projects?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>

        <TabsContent value="members" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Members</h2>
            <Button size="sm">
              <UserPlus className="mr-2 h-4 w-4" /> Invite Member
            </Button>
          </div>

          {membersLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <Skeleton className="h-12 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : members && members.length > 0 ? (
            <div className="space-y-2">
              {members.map((member) => (
                <Card key={member.id}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <Avatar>
                        <AvatarFallback>
                          {member.user_id ? "U" : "A"}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium font-mono text-sm">
                          {member.user_id || member.agent_id}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {member.user_id ? "User" : "Agent"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={member.role_name === "owner" ? "default" : "secondary"}>
                        {member.role_name}
                      </Badge>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>Change Role</DropdownMenuItem>
                          <DropdownMenuItem className="text-destructive">
                            Remove Member
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No members found.</p>
          )}
        </TabsContent>

        <TabsContent value="projects" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Projects</h2>
            <Button size="sm" asChild>
              <Link href="/projects/new">
                <FolderGit2 className="mr-2 h-4 w-4" /> New Project
              </Link>
            </Button>
          </div>

          {projects?.projects && projects.projects.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {projects.projects.slice(0, 4).map((project) => (
                <Card key={project.id}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">
                      <Link href={`/projects/${project.id}`} className="hover:underline">
                        {project.name}
                      </Link>
                    </CardTitle>
                    {project.github_repo && (
                      <CardDescription>
                        {project.github_owner}/{project.github_repo}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Phase: {project.default_phase_id}</span>
                      <Badge variant={project.status === "active" ? "default" : "secondary"}>
                        {project.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No projects found.</p>
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Organization Details</CardTitle>
              <CardDescription>Configuration and billing information</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Billing Email</p>
                  <p className="text-sm">{org.billing_email || "Not set"}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Created</p>
                  <p className="text-sm">{new Date(org.created_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Last Updated</p>
                  <p className="text-sm">{new Date(org.updated_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Owner ID</p>
                  <p className="text-sm font-mono">{org.owner_id}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
