"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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
  Mail,
  Clock,
  Loader2,
  Check,
  X,
} from "lucide-react"

interface OrganizationMembersPageProps {
  params: Promise<{ id: string }>
}

// Mock members data
const mockMembers = [
  {
    id: "1",
    name: "John Doe",
    email: "john@acme.com",
    role: "owner",
    avatar: null,
    joinedAt: "Jan 15, 2024",
    lastActive: "2 hours ago",
  },
  {
    id: "2",
    name: "Jane Smith",
    email: "jane@acme.com",
    role: "admin",
    avatar: null,
    joinedAt: "Feb 1, 2024",
    lastActive: "1 day ago",
  },
  {
    id: "3",
    name: "Bob Wilson",
    email: "bob@acme.com",
    role: "member",
    avatar: null,
    joinedAt: "Mar 10, 2024",
    lastActive: "5 hours ago",
  },
  {
    id: "4",
    name: "Alice Johnson",
    email: "alice@acme.com",
    role: "member",
    avatar: null,
    joinedAt: "Mar 15, 2024",
    lastActive: "Just now",
  },
  {
    id: "5",
    name: "Charlie Brown",
    email: "charlie@acme.com",
    role: "member",
    avatar: null,
    joinedAt: "Apr 1, 2024",
    lastActive: "3 days ago",
  },
]

// Mock pending invites
const mockInvites = [
  { id: "inv-1", email: "newuser@example.com", role: "member", sentAt: "2 days ago", expiresIn: "5 days" },
  { id: "inv-2", email: "developer@company.com", role: "admin", sentAt: "1 week ago", expiresIn: "Expired" },
]

const roleConfig = {
  owner: { icon: Crown, color: "text-amber-500", label: "Owner", description: "Full access to all resources" },
  admin: { icon: ShieldCheck, color: "text-blue-500", label: "Admin", description: "Can manage members and settings" },
  member: { icon: Shield, color: "text-gray-500", label: "Member", description: "Can access projects and resources" },
}

export default function OrganizationMembersPage({ params }: OrganizationMembersPageProps) {
  const { id } = use(params)
  const [searchQuery, setSearchQuery] = useState("")
  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [isInviting, setIsInviting] = useState(false)
  const [inviteData, setInviteData] = useState({ email: "", role: "member" })

  const filteredMembers = mockMembers.filter(
    (member) =>
      member.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.email.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleInvite = async () => {
    setIsInviting(true)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsInviting(false)
    setIsInviteOpen(false)
    setInviteData({ email: "", role: "member" })
    toast.success(`Invitation sent to ${inviteData.email}`)
  }

  const handleRoleChange = (memberId: string, newRole: string) => {
    toast.success("Member role updated")
  }

  const handleRemoveMember = (memberId: string) => {
    toast.success("Member removed from organization")
  }

  const handleCancelInvite = (inviteId: string) => {
    toast.success("Invitation cancelled")
  }

  const handleResendInvite = (inviteId: string) => {
    toast.success("Invitation resent")
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
              Invite Member
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite Member</DialogTitle>
              <DialogDescription>
                Send an invitation to join your organization
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="colleague@company.com"
                  value={inviteData.email}
                  onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select
                  value={inviteData.role}
                  onValueChange={(value) => setInviteData({ ...inviteData, role: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="member">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-gray-500" />
                        <div>
                          <p>Member</p>
                          <p className="text-xs text-muted-foreground">Can access projects and resources</p>
                        </div>
                      </div>
                    </SelectItem>
                    <SelectItem value="admin">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-blue-500" />
                        <div>
                          <p>Admin</p>
                          <p className="text-xs text-muted-foreground">Can manage members and settings</p>
                        </div>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsInviteOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleInvite} disabled={!inviteData.email || isInviting}>
                {isInviting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Send Invitation
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

      {/* Members Table */}
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>{mockMembers.length} members in this organization</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMembers.map((member) => {
                const config = roleConfig[member.role as keyof typeof roleConfig]
                const RoleIcon = config.icon

                return (
                  <TableRow key={member.id}>
                    <TableCell>
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
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="gap-1">
                        <RoleIcon className={`h-3 w-3 ${config.color}`} />
                        {config.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{member.joinedAt}</TableCell>
                    <TableCell className="text-muted-foreground">{member.lastActive}</TableCell>
                    <TableCell>
                      {member.role !== "owner" && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleRoleChange(member.id, "admin")}>
                              <ShieldCheck className="mr-2 h-4 w-4" />
                              Make Admin
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleRoleChange(member.id, "member")}>
                              <Shield className="mr-2 h-4 w-4" />
                              Make Member
                            </DropdownMenuItem>
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
                                    Are you sure you want to remove {member.name} from this
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
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>

          {filteredMembers.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No members found matching your search
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Invitations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Pending Invitations
          </CardTitle>
          <CardDescription>
            {mockInvites.length} pending invitations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mockInvites.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No pending invitations
            </p>
          ) : (
            <div className="space-y-3">
              {mockInvites.map((invite) => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>
                        {invite.email.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{invite.email}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>Sent {invite.sentAt}</span>
                        <span>•</span>
                        <span className={invite.expiresIn === "Expired" ? "text-destructive" : ""}>
                          {invite.expiresIn === "Expired" ? "Expired" : `Expires in ${invite.expiresIn}`}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">
                      {invite.role}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleResendInvite(invite.id)}
                    >
                      Resend
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCancelInvite(invite.id)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Role Legend */}
      <Card>
        <CardHeader>
          <CardTitle>Role Permissions</CardTitle>
          <CardDescription>Understanding member roles and their capabilities</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {Object.entries(roleConfig).map(([key, config]) => {
              const Icon = config.icon
              return (
                <div key={key} className="rounded-lg border p-4">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-5 w-5 ${config.color}`} />
                    <span className="font-medium">{config.label}</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{config.description}</p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
