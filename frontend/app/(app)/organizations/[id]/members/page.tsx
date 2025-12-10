"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  ArrowLeft,
  Search,
  UserPlus,
  MoreHorizontal,
  Shield,
  ShieldCheck,
  Crown,
  AlertCircle,
  Loader2,
  X,
  Bot,
  User,
} from "lucide-react"
import { useMembers, useRoles, useAddMember, useUpdateMember, useRemoveMember } from "@/hooks/useOrganizations"

interface OrganizationMembersPageProps {
  params: Promise<{ id: string }>
}

const roleIcons: Record<string, typeof Shield> = {
  owner: Crown,
  admin: ShieldCheck,
  member: Shield,
}

const roleColors: Record<string, string> = {
  owner: "text-amber-500",
  admin: "text-blue-500",
  member: "text-gray-500",
}

export default function OrganizationMembersPage({ params }: OrganizationMembersPageProps) {
  const { id } = use(params)
  const [searchQuery, setSearchQuery] = useState("")
  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [inviteData, setInviteData] = useState({ userId: "", roleId: "" })

  const { data: members, isLoading: membersLoading, error: membersError } = useMembers(id)
  const { data: roles, isLoading: rolesLoading } = useRoles(id)
  const addMemberMutation = useAddMember()
  const updateMemberMutation = useUpdateMember()
  const removeMemberMutation = useRemoveMember()

  // Filter members based on search
  const filteredMembers = useMemo(() => {
    if (!members) return []
    if (!searchQuery) return members
    return members.filter(
      (member) =>
        member.role_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (member.user_id && member.user_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (member.agent_id && member.agent_id.toLowerCase().includes(searchQuery.toLowerCase()))
    )
  }, [members, searchQuery])

  const handleAddMember = async () => {
    if (!inviteData.roleId) {
      toast.error("Please select a role")
      return
    }
    try {
      await addMemberMutation.mutateAsync({
        orgId: id,
        data: { user_id: inviteData.userId || undefined, role_id: inviteData.roleId },
      })
      setIsInviteOpen(false)
      setInviteData({ userId: "", roleId: "" })
      toast.success("Member added successfully")
    } catch (err) {
      toast.error("Failed to add member")
    }
  }

  const handleRoleChange = async (memberId: string, newRoleId: string) => {
    try {
      await updateMemberMutation.mutateAsync({
        orgId: id,
        memberId,
        roleId: newRoleId,
      })
      toast.success("Member role updated")
    } catch (err) {
      toast.error("Failed to update role")
    }
  }

  const handleRemoveMember = async (memberId: string) => {
    try {
      await removeMemberMutation.mutateAsync({ orgId: id, memberId })
      toast.success("Member removed from organization")
    } catch (err) {
      toast.error("Failed to remove member")
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  return (
    <div className="container mx-auto max-w-5xl p-6 space-y-6">
      <Link
        href={`/organizations/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Organization
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Members</h1>
          <p className="text-muted-foreground">
            Manage team members and their permissions
          </p>
        </div>
        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogTrigger asChild>
            <Button>
              <UserPlus className="mr-2 h-4 w-4" />
              Add Member
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Member</DialogTitle>
              <DialogDescription>
                Add a new member to this organization
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="userId">User ID</Label>
                <Input
                  id="userId"
                  placeholder="Enter user ID"
                  value={inviteData.userId}
                  onChange={(e) => setInviteData({ ...inviteData, userId: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select
                  value={inviteData.roleId}
                  onValueChange={(value) => setInviteData({ ...inviteData, roleId: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {roles?.map((role) => (
                      <SelectItem key={role.id} value={role.id}>
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4" />
                          <span>{role.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsInviteOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAddMember} 
                disabled={!inviteData.roleId || addMemberMutation.isPending}
              >
                {addMemberMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Member
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search members..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8"
        />
      </div>

      {/* Loading State */}
      {membersLoading && (
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48 mt-1" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {membersError && (
        <Card className="border-destructive/50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-destructive/50" />
            <h3 className="mt-4 text-lg font-semibold">Failed to load members</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Please try refreshing the page.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Members Table */}
      {!membersLoading && !membersError && (
        <Card>
          <CardHeader>
            <CardTitle>Team Members</CardTitle>
            <CardDescription>{members?.length || 0} members in this organization</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMembers.map((member) => {
                  const roleName = member.role_name.toLowerCase()
                  const RoleIcon = roleIcons[roleName] || Shield
                  const roleColor = roleColors[roleName] || "text-gray-500"
                  const isAgent = !!member.agent_id
                  const displayId = member.user_id || member.agent_id || "Unknown"

                  return (
                    <TableRow key={member.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar>
                            <AvatarFallback>
                              {isAgent ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium font-mono text-sm">{displayId.slice(0, 8)}...</p>
                            <p className="text-xs text-muted-foreground">
                              {isAgent ? "Agent" : "User"}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="gap-1">
                          <RoleIcon className={`h-3 w-3 ${roleColor}`} />
                          {member.role_name}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(member.joined_at)}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {roles?.filter(r => r.id !== member.role_id).map((role) => (
                              <DropdownMenuItem 
                                key={role.id}
                                onClick={() => handleRoleChange(member.id, role.id)}
                              >
                                <Shield className="mr-2 h-4 w-4" />
                                Change to {role.name}
                              </DropdownMenuItem>
                            ))}
                            <DropdownMenuSeparator />
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <DropdownMenuItem
                                  onSelect={(e) => e.preventDefault()}
                                  className="text-destructive"
                                >
                                  <X className="mr-2 h-4 w-4" />
                                  Remove Member
                                </DropdownMenuItem>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Remove Member</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to remove this member from the
                                    organization? They will lose access to all projects and
                                    resources.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleRemoveMember(member.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Remove
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>

            {filteredMembers.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                {searchQuery ? "No members found matching your search" : "No members yet"}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Role Legend */}
      {!rolesLoading && roles && roles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available Roles</CardTitle>
            <CardDescription>Roles defined for this organization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {roles.map((role) => {
                const roleName = role.name.toLowerCase()
                const Icon = roleIcons[roleName] || Shield
                const color = roleColors[roleName] || "text-gray-500"
                return (
                  <div key={role.id} className="rounded-lg border p-4">
                    <div className="flex items-center gap-2">
                      <Icon className={`h-5 w-5 ${color}`} />
                      <span className="font-medium">{role.name}</span>
                      {role.is_system && (
                        <Badge variant="secondary" className="text-xs">System</Badge>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {role.description || "No description"}
                    </p>
                    {role.permissions.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {role.permissions.slice(0, 3).map((perm) => (
                          <Badge key={perm} variant="outline" className="text-xs">
                            {perm}
                          </Badge>
                        ))}
                        {role.permissions.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{role.permissions.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
