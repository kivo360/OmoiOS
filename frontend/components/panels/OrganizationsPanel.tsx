"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Plus,
  Users,
  Check,
  Settings,
  Building2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrganizations } from "@/hooks/useOrganizations";

export function OrganizationsPanel() {
  const pathname = usePathname();
  const { data: organizations, isLoading, error } = useOrganizations();

  // Extract org ID from path if viewing a specific org
  // Exclude "new" since that's the create organization page, not a valid org ID
  const orgIdMatch = pathname.match(/\/organizations\/([^/]+)/);
  const extractedId = orgIdMatch?.[1];
  const isValidOrgId = extractedId && extractedId !== "new";
  const firstOrg = organizations?.[0];
  const currentOrgId = isValidOrgId ? extractedId : firstOrg?.id;

  const quickLinks = currentOrgId
    ? [
        {
          href: `/organizations/${currentOrgId}`,
          label: "Overview",
          icon: Building2,
        },
        {
          href: `/organizations/${currentOrgId}/members`,
          label: "Members",
          icon: Users,
        },
        {
          href: `/organizations/${currentOrgId}/settings`,
          label: "Settings",
          icon: Settings,
        },
      ]
    : [];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div>
          <h3 className="font-semibold">Organizations</h3>
          <p className="text-xs text-muted-foreground">
            Switch or manage teams
          </p>
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/organizations/new">
            <Plus className="mr-2 h-4 w-4" /> New Organization
          </Link>
        </Button>
      </div>

      {/* Quick Links for Current Org */}
      {currentOrgId && quickLinks.length > 0 && (
        <div className="border-b p-3 space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Quick Access
          </p>
          {quickLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </div>
      )}

      {/* Organization List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            All Organizations
          </p>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-md" />
              ))}
            </div>
          ) : error ? (
            <div className="py-4 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-6 w-6 mx-auto mb-2 opacity-50" />
              Failed to load
            </div>
          ) : organizations?.length === 0 ? (
            <div className="py-4 text-center text-sm text-muted-foreground">
              No organizations
            </div>
          ) : (
            organizations?.map((org) => {
              const isCurrentOrg = org.id === currentOrgId;
              return (
                <Link
                  key={org.id}
                  href={`/organizations/${org.id}`}
                  className={cn(
                    "flex items-center gap-3 rounded-md p-2 transition-colors",
                    isCurrentOrg ? "bg-accent" : "hover:bg-accent",
                  )}
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary/10 text-primary text-xs">
                      {org.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">
                        {org.name}
                      </span>
                      {isCurrentOrg && (
                        <Check className="h-3 w-3 text-success shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="secondary" className="text-[10px] h-4">
                        {org.role}
                      </Badge>
                    </div>
                  </div>
                </Link>
              );
            })
          )}
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
  );
}
