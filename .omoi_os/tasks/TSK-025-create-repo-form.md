---
id: TSK-025
title: Implement CreateRepoForm component
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-010
estimate: L
dependencies:
  depends_on:
    - TSK-024
  blocks: []
---

# TSK-025: Implement CreateRepoForm component

## Objective

Build the main form for creating new repositories with all fields integrated.

## Deliverables

- [ ] `frontend/components/project/CreateRepoForm.tsx`

## Implementation Notes

```tsx
// frontend/components/project/CreateRepoForm.tsx

"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { OwnerSelector } from "./OwnerSelector"
import { RepoNameInput } from "./RepoNameInput"
import { TemplateSelector } from "./TemplateSelector"
import { useCreateRepository } from "@/hooks/useGitHub"
import { Loader2 } from "lucide-react"

const formSchema = z.object({
  owner: z.string().min(1, "Please select an owner"),
  name: z.string().min(1).max(100),
  description: z.string().max(350).optional(),
  visibility: z.enum(["private", "public"]),
  template: z.enum(["empty", "nextjs", "fastapi", "react-vite", "python-package"]),
  featureDescription: z.string().optional(),
})

type FormData = z.infer<typeof formSchema>

interface CreateRepoFormProps {
  onSuccess: (projectId: string) => void
}

export function CreateRepoForm({ onSuccess }: CreateRepoFormProps) {
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null)
  const createRepo = useCreateRepository()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      visibility: "private",
      template: "empty",
    },
  })

  const selectedOwner = form.watch("owner")
  const repoName = form.watch("name")

  const onSubmit = async (data: FormData) => {
    try {
      const result = await createRepo.mutateAsync({
        name: data.name,
        owner: data.owner,
        description: data.description,
        visibility: data.visibility,
        template: data.template,
        auto_scaffold: !!data.featureDescription,
        feature_description: data.featureDescription,
      })
      onSuccess(result.project_id)
    } catch (error) {
      // Error handling via toast
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      {/* Owner Selection */}
      <div className="space-y-2">
        <Label>Owner</Label>
        <OwnerSelector
          value={selectedOwner}
          onChange={(value) => form.setValue("owner", value)}
        />
      </div>

      {/* Repository Name */}
      <div className="space-y-2">
        <Label>Repository Name</Label>
        <RepoNameInput
          owner={selectedOwner}
          value={repoName}
          onChange={(value) => form.setValue("name", value)}
          onAvailabilityChange={setIsAvailable}
        />
      </div>

      {/* Description */}
      <div className="space-y-2">
        <Label>Description (optional)</Label>
        <Input
          {...form.register("description")}
          placeholder="A short description of your project"
        />
      </div>

      {/* Visibility */}
      <div className="space-y-2">
        <Label>Visibility</Label>
        <RadioGroup
          value={form.watch("visibility")}
          onValueChange={(v) => form.setValue("visibility", v as "private" | "public")}
          className="flex gap-4"
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="private" id="private" />
            <Label htmlFor="private">Private</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="public" id="public" />
            <Label htmlFor="public">Public</Label>
          </div>
        </RadioGroup>
      </div>

      {/* Template */}
      <div className="space-y-2">
        <Label>Starter Template</Label>
        <TemplateSelector
          value={form.watch("template")}
          onChange={(v) => form.setValue("template", v)}
        />
      </div>

      {/* Feature Description */}
      <div className="space-y-2">
        <Label>What do you want to build? (optional)</Label>
        <Textarea
          {...form.register("featureDescription")}
          placeholder="Describe the features you want... AI agents will scaffold and start building."
          rows={4}
        />
        <p className="text-sm text-muted-foreground">
          If provided, AI agents will automatically start building based on your description.
        </p>
      </div>

      {/* Submit */}
      <Button
        type="submit"
        className="w-full"
        disabled={!isAvailable || !selectedOwner || createRepo.isPending}
      >
        {createRepo.isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Creating...
          </>
        ) : (
          "Create Repository & Start Building"
        )}
      </Button>
    </form>
  )
}
```

## Done When

- [ ] Form renders with all fields
- [ ] Validation works
- [ ] Submit creates repo and triggers onSuccess
- [ ] Loading state during creation
- [ ] Error handling
