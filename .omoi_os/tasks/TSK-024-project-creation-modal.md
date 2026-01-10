---
id: TSK-024
title: Create ProjectCreationModal with tabs
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-010
estimate: M
dependencies:
  depends_on:
    - TSK-010
  blocks:
    - TSK-025
---

# TSK-024: Create ProjectCreationModal with tabs

## Objective

Build the main project creation modal with tabs for "Create New Repo" and "Connect Existing".

## Deliverables

- [ ] `frontend/components/project/ProjectCreationModal.tsx`

## Implementation Notes

```tsx
// frontend/components/project/ProjectCreationModal.tsx

"use client"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CreateRepoForm } from "./CreateRepoForm"
import { ConnectRepoForm } from "./ConnectRepoForm"

interface ProjectCreationModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (projectId: string) => void
}

export function ProjectCreationModal({
  open,
  onOpenChange,
  onSuccess,
}: ProjectCreationModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New Project</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="create" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="create">Create New Repo</TabsTrigger>
            <TabsTrigger value="connect">Connect Existing</TabsTrigger>
          </TabsList>

          <TabsContent value="create" className="mt-4">
            <CreateRepoForm
              onSuccess={(projectId) => {
                onSuccess(projectId)
                onOpenChange(false)
              }}
            />
          </TabsContent>

          <TabsContent value="connect" className="mt-4">
            <ConnectRepoForm
              onSuccess={(projectId) => {
                onSuccess(projectId)
                onOpenChange(false)
              }}
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
```

## Done When

- [ ] Modal component created
- [ ] Tabs switch between Create/Connect
- [ ] Proper dialog behavior (close, open)
- [ ] Consistent with existing UI patterns
