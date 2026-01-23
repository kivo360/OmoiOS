"use client"

import { useState, useEffect } from "react"
import {
  useSpecDrivenSettings,
  useUpdateSpecDrivenSettings,
} from "@/hooks/useSpecDrivenSettings"
import type { SpecDrivenOptions } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  AlertCircle,
  AlertTriangle,
  HelpCircle,
  Loader2,
  RefreshCw,
} from "lucide-react"

interface SpecDrivenSettingsPanelProps {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const DEFAULT_SETTINGS: SpecDrivenOptions = {
  spec_driven_mode_enabled: false,
  auto_advance_phases: true,
  require_approval_gates: false,
  auto_spawn_tasks: true,
}

interface SettingConfig {
  key: keyof SpecDrivenOptions
  label: string
  description: string
  helpText: string
  isRisky?: boolean
  riskWarning?: string
}

const SETTINGS_CONFIG: SettingConfig[] = [
  {
    key: "spec_driven_mode_enabled",
    label: "Enable Spec-Driven Mode",
    description: "Enable spec-driven workflow for this project",
    helpText:
      "When enabled, tickets can use the spec-driven workflow which creates structured specifications before implementation.",
  },
  {
    key: "auto_advance_phases",
    label: "Auto-Advance Phases",
    description: "Automatically progress through spec phases",
    helpText:
      "Automatically advance through EXPLORE, REQUIREMENTS, DESIGN, TASKS, and SYNC phases without manual intervention.",
    isRisky: true,
    riskWarning:
      "Disabling this requires manual phase advancement, which may slow down workflow.",
  },
  {
    key: "require_approval_gates",
    label: "Require Approval Gates",
    description: "Pause at phase gates for approval",
    helpText:
      "Require manual approval at each phase gate before advancing. Useful for review-heavy workflows.",
  },
  {
    key: "auto_spawn_tasks",
    label: "Auto-Spawn Tasks",
    description: "Automatically create implementation tasks",
    helpText:
      "Automatically spawn implementation tasks after the SYNC phase completes.",
    isRisky: true,
    riskWarning:
      "Disabling this requires manual task creation after spec completion.",
  },
]

export function SpecDrivenSettingsPanel({
  projectId,
  open,
  onOpenChange,
}: SpecDrivenSettingsPanelProps) {
  const {
    data: settings,
    isLoading,
    error,
    refetch,
  } = useSpecDrivenSettings(projectId)
  const updateSettings = useUpdateSpecDrivenSettings()

  const [formState, setFormState] = useState<SpecDrivenOptions | null>(null)
  const [isDirty, setIsDirty] = useState(false)

  // Sync form state when settings load
  useEffect(() => {
    if (settings) {
      setFormState(settings)
      setIsDirty(false)
    }
  }, [settings])

  // Check if form has unsaved changes
  const hasUnsavedChanges = isDirty && formState !== null

  const handleSettingChange = (key: keyof SpecDrivenOptions, value: boolean) => {
    if (!formState) return

    setFormState((prev) => {
      if (!prev) return prev
      return { ...prev, [key]: value }
    })
    setIsDirty(true)
  }

  const handleSave = async () => {
    if (!formState) return

    try {
      await updateSettings.mutateAsync({
        projectId,
        settings: formState,
      })
      setIsDirty(false)
      onOpenChange(false)
    } catch {
      // Error handled by mutation
    }
  }

  const handleReset = () => {
    if (settings) {
      setFormState(settings)
      setIsDirty(false)
    }
  }

  const handleCancel = () => {
    if (hasUnsavedChanges) {
      // Could add confirmation dialog here
      handleReset()
    }
    onOpenChange(false)
  }

  const handleRetry = () => {
    refetch()
  }

  // Get current form values or defaults
  const currentSettings = formState ?? DEFAULT_SETTINGS

  // Check for risky configurations
  const hasRiskyConfig = SETTINGS_CONFIG.some(
    (config) =>
      config.isRisky &&
      currentSettings[config.key] !== DEFAULT_SETTINGS[config.key]
  )

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[480px] flex flex-col">
        <SheetHeader>
          <SheetTitle>Spec-Driven Settings</SheetTitle>
          <SheetDescription>
            Configure how spec-driven development workflows behave for this
            project.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-6">
          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="space-y-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error
                    ? error.message
                    : "Failed to load settings"}
                </AlertDescription>
              </Alert>
              <Button
                variant="outline"
                onClick={handleRetry}
                className="w-full"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </div>
          )}

          {/* Settings Form */}
          {!isLoading && !error && formState && (
            <TooltipProvider>
              <div className="space-y-6">
                {SETTINGS_CONFIG.map((config) => (
                  <div
                    key={config.key}
                    className="flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <Label
                          htmlFor={config.key}
                          className="text-sm font-medium"
                        >
                          {config.label}
                        </Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent
                            side="top"
                            className="max-w-[280px] text-sm"
                          >
                            {config.helpText}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {config.description}
                      </p>
                      {/* Risk Warning */}
                      {config.isRisky &&
                        currentSettings[config.key] !==
                          DEFAULT_SETTINGS[config.key] && (
                          <div className="flex items-center gap-1.5 mt-1.5 text-xs text-amber-600 dark:text-amber-500">
                            <AlertTriangle className="h-3 w-3" />
                            <span>{config.riskWarning}</span>
                          </div>
                        )}
                    </div>
                    <Switch
                      id={config.key}
                      checked={currentSettings[config.key]}
                      onCheckedChange={(checked) =>
                        handleSettingChange(config.key, checked)
                      }
                      disabled={updateSettings.isPending}
                    />
                  </div>
                ))}

                {/* Global Risk Warning */}
                {hasRiskyConfig && (
                  <Alert className="border-amber-500/50 bg-amber-500/10">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-amber-700 dark:text-amber-400">
                      Some settings have been changed from their recommended
                      defaults. Review the warnings above before saving.
                    </AlertDescription>
                  </Alert>
                )}

                {/* Save Error */}
                {updateSettings.isError && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {updateSettings.error instanceof Error
                        ? updateSettings.error.message
                        : "Failed to save settings"}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </TooltipProvider>
          )}
        </div>

        <SheetFooter className="flex-shrink-0 border-t pt-4">
          <div className="flex w-full gap-2 sm:flex-row-reverse">
            <Button
              onClick={handleSave}
              disabled={
                !isDirty || updateSettings.isPending || isLoading || !!error
              }
            >
              {updateSettings.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Changes
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={
                !isDirty || updateSettings.isPending || isLoading || !!error
              }
            >
              Reset
            </Button>
            <Button
              variant="ghost"
              onClick={handleCancel}
              disabled={updateSettings.isPending}
            >
              Cancel
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
