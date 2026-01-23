"use client"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

interface SpecDrivenSettingsPanelProps {
  projectId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SpecDrivenSettingsPanel({
  projectId,
  open,
  onOpenChange,
}: SpecDrivenSettingsPanelProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Spec-Driven Settings</SheetTitle>
          <SheetDescription>
            Configure spec-driven workflow settings for your project.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {projectId ? (
            <p className="text-sm text-muted-foreground">
              Project ID: {projectId}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              No project selected. Select a project to configure settings.
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
