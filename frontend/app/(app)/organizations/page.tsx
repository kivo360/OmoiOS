"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Search,
  Plus,
  Building2,
  Users,
  FolderGit2,
  Settings,
  MoreHorizontal,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// Mock organizations
const mockOrganizations = [
  {
    id: "org-001",
    name: "Acme Inc",
    slug: "acme-inc",
    avatar: null,
    role: "owner",
    memberCount: 12,
    projectCount: 5,
    plan: "pro",
  },
  {
    id: "org-002",
    name: "Personal",
    slug: "personal",
    avatar: null,
    role: "owner",
    memberCount: 1,
    projectCount: 3,
    plan: "free",
  },
  {
    id: "org-003",
    name: "Open Source Collective",
    slug: "oss-collective",
    avatar: null,
    role: "member",
    memberCount: 48,
    projectCount: 15,
    plan: "enterprise",
  },
]

export default function OrganizationsPage() {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredOrgs = mockOrganizations.filter((org) =>
    org.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Organizations</h1>
          <p className="text-muted-foreground">
            Manage your organizations and teams
          </p>
        </div>
        <Button asChild>
          <Link href="/organizations/new">
            <Plus className="mr-2 h-4 w-4" /> New Organization
          </Link>
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search organizations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8"
        />
      </div>

      {/* Organizations List */}
      <div className="space-y-4">
        {filteredOrgs.map((org) => (
          <Card key={org.id} className="hover:border-primary/50 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <Avatar className="h-12 w-12">
                    <AvatarImage src={org.avatar || undefined} />
                    <AvatarFallback className="bg-primary/10 text-primary">
                      {org.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/organizations/${org.id}`}
                        className="font-semibold hover:underline"
                      >
                        {org.name}
                      </Link>
                      <Badge variant={org.role === "owner" ? "default" : "secondary"}>
                        {org.role}
                      </Badge>
                      <Badge variant="outline" className="capitalize">
                        {org.plan}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">@{org.slug}</p>
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                      <Link href={`/organizations/${org.id}`}>
                        <Building2 className="mr-2 h-4 w-4" /> View
                      </Link>
                    </DropdownMenuItem>
                    {org.role === "owner" && (
                      <DropdownMenuItem asChild>
                        <Link href={`/organizations/${org.id}/settings`}>
                          <Settings className="mr-2 h-4 w-4" /> Settings
                        </Link>
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <div className="mt-4 flex items-center gap-6 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Users className="h-4 w-4" />
                  {org.memberCount} member{org.memberCount !== 1 ? "s" : ""}
                </span>
                <span className="flex items-center gap-1">
                  <FolderGit2 className="h-4 w-4" />
                  {org.projectCount} project{org.projectCount !== 1 ? "s" : ""}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredOrgs.length === 0 && (
        <Card className="p-12 text-center">
          <Building2 className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No organizations found</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {searchQuery
              ? "Try adjusting your search"
              : "Create your first organization to get started"}
          </p>
          <Button className="mt-4" asChild>
            <Link href="/organizations/new">
              <Plus className="mr-2 h-4 w-4" /> Create Organization
            </Link>
          </Button>
        </Card>
      )}
    </div>
  )
}
