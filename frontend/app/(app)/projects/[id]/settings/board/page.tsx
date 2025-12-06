"use client"

import { use, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  ArrowLeft,
  Settings,
  Columns3,
  GitBranch,
  Workflow,
  GripVertical,
  Plus,
  Pencil,
  Trash2,
  Save,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { mockProjects } from "@/lib/mock"

interface BoardSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

// Mock board columns data
const mockColumns = [
  { id: "backlog", name: "Backlog", phaseMapping: "PHASE_BACKLOG", wipLimit: 0, color: "#6B7280" },
  { id: "todo", name: "To Do", phaseMapping: "PHASE_REQUIREMENTS", wipLimit: 10, color: "#3B82F6" },
  { id: "in-progress", name: "In Progress", phaseMapping: "PHASE_IMPLEMENTATION", wipLimit: 5, color: "#F59E0B" },
  { id: "review", name: "Review", phaseMapping: "PHASE_TESTING", wipLimit: 3, color: "#8B5CF6" },
  { id: "done", name: "Done", phaseMapping: "PHASE_DONE", wipLimit: 0, color: "#10B981" },
]

const mockTicketTypes = [
  { id: "feature", name: "Feature", color: "#3B82F6", icon: "✨" },
  { id: "bug", name: "Bug", color: "#EF4444", icon: "🐛" },
  { id: "task", name: "Task", color: "#6B7280", icon: "📋" },
  { id: "improvement", name: "Improvement", color: "#10B981", icon: "⬆️" },
]

const phases = [
  "PHASE_BACKLOG",
  "PHASE_REQUIREMENTS",
  "PHASE_DESIGN",
  "PHASE_IMPLEMENTATION",
  "PHASE_TESTING",
  "PHASE_DEPLOYMENT",
  "PHASE_DONE",
]

export default function BoardSettingsPage({ params }: BoardSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  const project = mockProjects.find((p) => p.id === id)
  const [columns, setColumns] = useState(mockColumns)
  const [ticketTypes, setTicketTypes] = useState(mockTicketTypes)
  const [isAddColumnOpen, setIsAddColumnOpen] = useState(false)
  const [isAddTypeOpen, setIsAddTypeOpen] = useState(false)

  if (!project) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href={`/projects/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to {project.name}
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Project Settings</h1>
        <p className="text-muted-foreground">Manage settings for {project.name}</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <nav className="w-48 shrink-0 space-y-1">
          {settingsNav.map((item) => {
            const isActive = pathname === `/projects/${id}/settings${item.href}`
            return (
              <Link
                key={item.href}
                href={`/projects/${id}/settings${item.href}`}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          {/* Board Columns */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Board Columns</CardTitle>
                <CardDescription>Configure kanban board columns and their phase mappings</CardDescription>
              </div>
              <Dialog open={isAddColumnOpen} onOpenChange={setIsAddColumnOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Column
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Column</DialogTitle>
                    <DialogDescription>
                      Create a new column for your kanban board
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="columnName">Column Name</Label>
                      <Input id="columnName" placeholder="e.g., Code Review" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phaseMapping">Phase Mapping</Label>
                      <Select>
                        <SelectTrigger id="phaseMapping">
                          <SelectValue placeholder="Select phase" />
                        </SelectTrigger>
                        <SelectContent>
                          {phases.map((phase) => (
                            <SelectItem key={phase} value={phase}>
                              {phase.replace("PHASE_", "").replace(/_/g, " ")}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="wipLimit">WIP Limit (0 = unlimited)</Label>
                      <Input id="wipLimit" type="number" min="0" defaultValue="0" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsAddColumnOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => setIsAddColumnOpen(false)}>Add Column</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {columns.map((column, index) => (
                  <div
                    key={column.id}
                    className="flex items-center gap-3 rounded-lg border p-3"
                  >
                    <GripVertical className="h-4 w-4 cursor-grab text-muted-foreground" />
                    <div
                      className="h-4 w-4 rounded"
                      style={{ backgroundColor: column.color }}
                    />
                    <div className="flex-1">
                      <p className="font-medium">{column.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {column.phaseMapping.replace("PHASE_", "").replace(/_/g, " ")}
                      </p>
                    </div>
                    {column.wipLimit > 0 && (
                      <Badge variant="secondary">WIP: {column.wipLimit}</Badge>
                    )}
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Drag columns to reorder. Column order determines display order on the board.
              </p>
            </CardContent>
          </Card>

          {/* Ticket Types */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Ticket Types</CardTitle>
                <CardDescription>Configure the types of tickets available in this project</CardDescription>
              </div>
              <Dialog open={isAddTypeOpen} onOpenChange={setIsAddTypeOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Type
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Ticket Type</DialogTitle>
                    <DialogDescription>
                      Create a new ticket type for your project
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="typeName">Type Name</Label>
                      <Input id="typeName" placeholder="e.g., Epic" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="typeIcon">Icon (emoji)</Label>
                      <Input id="typeIcon" placeholder="e.g., 🎯" maxLength={2} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="typeColor">Color</Label>
                      <Input id="typeColor" type="color" defaultValue="#6B7280" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsAddTypeOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => setIsAddTypeOpen(false)}>Add Type</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                {ticketTypes.map((type) => (
                  <div
                    key={type.id}
                    className="flex items-center gap-3 rounded-lg border p-3"
                  >
                    <span className="text-lg">{type.icon}</span>
                    <div className="flex-1">
                      <p className="font-medium">{type.name}</p>
                    </div>
                    <div
                      className="h-4 w-4 rounded"
                      style={{ backgroundColor: type.color }}
                    />
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Default Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Default Settings</CardTitle>
              <CardDescription>Configure default values for new tickets</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="defaultType">Default Ticket Type</Label>
                  <Select defaultValue="task">
                    <SelectTrigger id="defaultType">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ticketTypes.map((type) => (
                        <SelectItem key={type.id} value={type.id}>
                          <span className="flex items-center gap-2">
                            <span>{type.icon}</span>
                            {type.name}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="initialStatus">Initial Status</Label>
                  <Select defaultValue="backlog">
                    <SelectTrigger id="initialStatus">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {columns.map((column) => (
                        <SelectItem key={column.id} value={column.id}>
                          {column.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Auto-Transitions */}
          <Card>
            <CardHeader>
              <CardTitle>Auto-Transitions</CardTitle>
              <CardDescription>Configure automatic ticket status transitions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-transition on phase completion</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically move tickets when their phase completes
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-unblock when blocker resolves</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically remove blocking status when blocker is done
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-assign agents on status change</Label>
                  <p className="text-sm text-muted-foreground">
                    Spawn agents when tickets move to specific columns
                  </p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
