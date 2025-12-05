"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Plus, Users, Check } from "lucide-react"

const mockOrganizations = [
  {
    id: "org-001",
    name: "Acme Inc",
    slug: "acme-inc",
    role: "owner",
    memberCount: 12,
    isActive: true,
  },
  {
    id: "org-002",
    name: "Personal",
    slug: "personal",
    role: "owner",
    memberCount: 1,
    isActive: false,
  },
  {
    id: "org-003",
    name: "Open Source Collective",
    slug: "oss-collective",
    role: "member",
    memberCount: 48,
    isActive: false,
  },
]

export function OrganizationsPanel() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div>
          <h3 className="font-semibold">Organizations</h3>
          <p className="text-xs text-muted-foreground">Switch or manage teams</p>
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/organizations/new">
            <Plus className="mr-2 h-4 w-4" /> New Organization
          </Link>
        </Button>
      </div>

      {/* Organization List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          {mockOrganizations.map((org) => (
            <Link
              key={org.id}
              href={`/organizations/${org.id}`}
              className="flex items-center gap-3 rounded-md p-2 hover:bg-accent transition-colors"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">
                  {org.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{org.name}</span>
                  {org.isActive && (
                    <Check className="h-3 w-3 text-success shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Users className="h-3 w-3" />
                  <span>{org.memberCount}</span>
                  <Badge variant="secondary" className="text-[10px] h-4">
                    {org.role}
                  </Badge>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-3">
        <Link
          href="/organizations"
          className="block text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Manage organizations →
        </Link>
      </div>
    </div>
  )
}
