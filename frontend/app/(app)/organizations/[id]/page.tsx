"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowLeft,
  Settings,
  Users,
  FolderGit2,
  Building2,
  UserPlus,
  MoreHorizontal,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { mockProjects } from "@/lib/mock"

interface OrganizationPageProps {
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
}

// Mock members
const mockMembers = [
  { id: "1", name: "John Doe", email: "john@acme.com", role: "owner", avatar: null },
  { id: "2", name: "Jane Smith", email: "jane@acme.com", role: "admin", avatar: null },
  { id: "3", name: "Bob Wilson", email: "bob@acme.com", role: "member", avatar: null },
]

export default function OrganizationPage({ params }: OrganizationPageProps) {
  const { id } = use(params)

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
            <AvatarImage src={mockOrg.avatar || undefined} />
            <AvatarFallback className="bg-primary/10 text-primary text-xl">
              {mockOrg.name.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{mockOrg.name}</h1>
              <Badge variant="outline" className="capitalize">
                {mockOrg.plan}
              </Badge>
            </div>
            <p className="text-muted-foreground">@{mockOrg.slug}</p>
            {mockOrg.description && (
              <p className="mt-1 text-sm text-muted-foreground">{mockOrg.description}</p>
            )}
          </div>
        </div>
        <Button variant="outline" asChild>
          <Link href={`/organizations/${id}/settings`}>
            <Settings className="mr-2 h-4 w-4" /> Settings
          </Link>
        </Button>
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
                <p className="text-2xl font-bold">{mockOrg.memberCount}</p>
                <p className="text-sm text-muted-foreground">Members</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <FolderGit2 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{mockOrg.projectCount}</p>
                <p className="text-sm text-muted-foreground">Projects</p>
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
                <p className="text-2xl font-bold capitalize">{mockOrg.plan}</p>
                <p className="text-sm text-muted-foreground">Plan</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="members" className="space-y-4">
        <TabsList>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="projects">Projects</TabsTrigger>
        </TabsList>

        <TabsContent value="members" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Members</h2>
            <Button size="sm">
              <UserPlus className="mr-2 h-4 w-4" /> Invite Member
            </Button>
          </div>

          <div className="space-y-2">
            {mockMembers.map((member) => (
              <Card key={member.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarImage src={member.avatar || undefined} />
                      <AvatarFallback>
                        {member.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-muted-foreground">{member.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={member.role === "owner" ? "default" : "secondary"}>
                      {member.role}
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

          <div className="grid gap-4 md:grid-cols-2">
            {mockProjects.slice(0, 4).map((project) => (
              <Card key={project.id}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">
                    <Link href={`/projects/${project.id}`} className="hover:underline">
                      {project.name}
                    </Link>
                  </CardTitle>
                  <CardDescription>{project.repo}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{project.ticketCount} tickets</span>
                    <Badge variant={project.status === "active" ? "default" : "secondary"}>
                      {project.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
