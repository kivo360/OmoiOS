"use client"

import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Loader2, AlertTriangle, Settings2, RotateCcw, Save } from "lucide-react"
import {
  useSpecDrivenSettings,
  useUpdateSpecDrivenSettings,
  useResetSpecDrivenSettings,
  DEFAULT_SETTINGS,
  getSettingsWarnings,
  validateSettings,
  type SpecDrivenSettings,
  type SpecDrivenSettingsUpdate,
  type SettingsWarning,
  type ValidationError,
} from "@/hooks/useSpecDrivenSettings"

interface SpecDrivenSettingsPanelProps {
  onClose?: () => void
}

export function SpecDrivenSettingsPanel({ onClose }: SpecDrivenSettingsPanelProps) {
  const { data: settings, isLoading, error } = useSpecDrivenSettings()
  const updateMutation = useUpdateSpecDrivenSettings()
  const resetMutation = useResetSpecDrivenSettings()

  // Local state for form
  const [localSettings, setLocalSettings] = useState<Partial<SpecDrivenSettings> | null>(null)
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  const [pendingClose, setPendingClose] = useState(false)

  // Sync settings to local state when loaded
  useEffect(() => {
    if (settings && !localSettings) {
      setLocalSettings(settings)
    }
  }, [settings, localSettings])

  // Check if there are unsaved changes
  const hasUnsavedChanges = useCallback(() => {
    if (!settings || !localSettings) return false
    return JSON.stringify(settings) !== JSON.stringify(localSettings)
  }, [settings, localSettings])

  // Get warnings and validation errors
  const warnings: SettingsWarning[] = localSettings ? getSettingsWarnings(localSettings) : []
  const validationErrors: ValidationError[] = localSettings ? validateSettings(localSettings) : []

  // Handle field changes
  const updateField = <K extends keyof SpecDrivenSettingsUpdate>(
    field: K,
    value: SpecDrivenSettingsUpdate[K]
  ) => {
    setLocalSettings((prev) => prev ? { ...prev, [field]: value } : null)
  }

  // Handle save
  const handleSave = async () => {
    if (!localSettings || validationErrors.length > 0) return

    try {
      await updateMutation.mutateAsync(localSettings as SpecDrivenSettingsUpdate)
      toast.success("Settings saved successfully")
    } catch (err) {
      toast.error("Failed to save settings")
    }
  }

  // Handle reset
  const handleReset = async () => {
    try {
      const result = await resetMutation.mutateAsync()
      setLocalSettings(result)
      toast.success("Settings reset to defaults")
    } catch (err) {
      toast.error("Failed to reset settings")
    }
  }

  // Handle close with unsaved changes check
  const handleClose = () => {
    if (hasUnsavedChanges()) {
      setPendingClose(true)
      setShowUnsavedDialog(true)
    } else {
      onClose?.()
    }
  }

  // Confirm discard changes
  const handleDiscardChanges = () => {
    setShowUnsavedDialog(false)
    if (pendingClose) {
      setPendingClose(false)
      onClose?.()
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <Card data-testid="settings-panel-loading">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Spec-Driven Settings
          </CardTitle>
          <CardDescription>Configure your spec-driven development workflow</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  // Error state
  if (error) {
    return (
      <Card data-testid="settings-panel-error">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Spec-Driven Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              Failed to load settings. Please try again.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  if (!localSettings) return null

  return (
    <>
      <Card data-testid="settings-panel">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                Spec-Driven Settings
              </CardTitle>
              <CardDescription>Configure your spec-driven development workflow</CardDescription>
            </div>
            {onClose && (
              <Button variant="ghost" size="sm" onClick={handleClose}>
                Close
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="space-y-2" data-testid="settings-warnings">
              {warnings.map((warning, index) => (
                <Alert
                  key={`${warning.field}-${index}`}
                  variant={warning.severity === "error" ? "destructive" : "default"}
                >
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{warning.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          )}

          {/* Execution Mode */}
          <div className="space-y-3">
            <Label className="text-base font-medium">Execution Mode</Label>
            <RadioGroup
              value={localSettings.execution_mode}
              onValueChange={(value) => updateField("execution_mode", value as "auto" | "manual")}
              data-testid="execution-mode-radio"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="auto" id="exec-auto" />
                <Label htmlFor="exec-auto" className="font-normal">
                  Automatic - Execute specs immediately
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="manual" id="exec-manual" />
                <Label htmlFor="exec-manual" className="font-normal">
                  Manual - Review specs before execution
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Auto Execute Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Auto Execute</Label>
              <p className="text-sm text-muted-foreground">
                Automatically start execution when spec is ready
              </p>
            </div>
            <Switch
              checked={localSettings.auto_execute}
              onCheckedChange={(checked) => updateField("auto_execute", checked)}
              data-testid="auto-execute-switch"
            />
          </div>

          {/* Coverage Threshold */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Coverage Threshold</Label>
              <span className="text-sm font-medium" data-testid="coverage-value">
                {localSettings.coverage_threshold}%
              </span>
            </div>
            <Slider
              value={[localSettings.coverage_threshold ?? DEFAULT_SETTINGS.coverage_threshold]}
              onValueChange={([value]) => updateField("coverage_threshold", value)}
              min={0}
              max={100}
              step={5}
              data-testid="coverage-slider"
            />
            {validationErrors.find((e) => e.field === "coverage_threshold") && (
              <p className="text-sm text-destructive" data-testid="coverage-error">
                {validationErrors.find((e) => e.field === "coverage_threshold")?.message}
              </p>
            )}
          </div>

          {/* Enforce Coverage Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Enforce Coverage</Label>
              <p className="text-sm text-muted-foreground">
                Block merges below threshold
              </p>
            </div>
            <Switch
              checked={localSettings.enforce_coverage}
              onCheckedChange={(checked) => updateField("enforce_coverage", checked)}
              data-testid="enforce-coverage-switch"
            />
          </div>

          {/* Parallel Execution Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Parallel Execution</Label>
              <p className="text-sm text-muted-foreground">
                Run multiple tasks simultaneously
              </p>
            </div>
            <Switch
              checked={localSettings.parallel_execution}
              onCheckedChange={(checked) => updateField("parallel_execution", checked)}
              data-testid="parallel-execution-switch"
            />
          </div>

          {/* Validation Mode */}
          <div className="space-y-3">
            <Label className="text-base font-medium">Validation Mode</Label>
            <RadioGroup
              value={localSettings.validation_mode}
              onValueChange={(value) => updateField("validation_mode", value as "strict" | "relaxed" | "none")}
              data-testid="validation-mode-radio"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="strict" id="val-strict" />
                <Label htmlFor="val-strict" className="font-normal">
                  Strict - All validations must pass
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="relaxed" id="val-relaxed" />
                <Label htmlFor="val-relaxed" className="font-normal">
                  Relaxed - Allow minor issues
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="none" id="val-none" />
                <Label htmlFor="val-none" className="font-normal">
                  None - Skip validation
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Require Tests Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Require Tests</Label>
              <p className="text-sm text-muted-foreground">
                All code must have tests
              </p>
            </div>
            <Switch
              checked={localSettings.require_tests}
              onCheckedChange={(checked) => updateField("require_tests", checked)}
              data-testid="require-tests-switch"
            />
          </div>

          {/* Require Docs Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Require Documentation</Label>
              <p className="text-sm text-muted-foreground">
                All code must have documentation
              </p>
            </div>
            <Switch
              checked={localSettings.require_docs}
              onCheckedChange={(checked) => updateField("require_docs", checked)}
              data-testid="require-docs-switch"
            />
          </div>

          {/* Auto Merge Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Auto Merge</Label>
              <p className="text-sm text-muted-foreground">
                Automatically merge passing PRs
              </p>
            </div>
            <Switch
              checked={localSettings.auto_merge}
              onCheckedChange={(checked) => updateField("auto_merge", checked)}
              data-testid="auto-merge-switch"
            />
          </div>

          {/* Notify on Completion Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base font-medium">Notify on Completion</Label>
              <p className="text-sm text-muted-foreground">
                Send notification when tasks complete
              </p>
            </div>
            <Switch
              checked={localSettings.notify_on_completion}
              onCheckedChange={(checked) => updateField("notify_on_completion", checked)}
              data-testid="notify-completion-switch"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t">
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={resetMutation.isPending}
              data-testid="reset-button"
            >
              {resetMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="mr-2 h-4 w-4" />
              )}
              Reset to Defaults
            </Button>
            <Button
              onClick={handleSave}
              disabled={updateMutation.isPending || validationErrors.length > 0}
              data-testid="save-button"
            >
              {updateMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Changes
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Unsaved Changes Dialog */}
      <AlertDialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
        <AlertDialogContent data-testid="unsaved-changes-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to close without saving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setShowUnsavedDialog(false)}>
              Keep Editing
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscardChanges}>
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
