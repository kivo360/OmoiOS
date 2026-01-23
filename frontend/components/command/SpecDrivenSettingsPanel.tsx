"use client"

import * as React from "react"
import { useState, useCallback, useMemo } from "react"
import { AlertTriangle, HelpCircle, Info, X } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
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
import { cn } from "@/lib/utils"

// Types for spec-driven settings
export interface SpecDrivenSettings {
  bypass_mode: boolean
  min_test_coverage: number
  auto_progression: boolean
  guardian_enabled: boolean
}

export interface SpecDrivenSettingsPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  settings?: SpecDrivenSettings
  onSave?: (settings: SpecDrivenSettings) => Promise<void>
  isLoading?: boolean
}

// Default settings
const defaultSettings: SpecDrivenSettings = {
  bypass_mode: false,
  min_test_coverage: 80,
  auto_progression: false,
  guardian_enabled: true,
}

// Tooltip descriptions for each setting
const tooltipDescriptions = {
  bypass_mode:
    "When enabled, quality gates are logged but not enforced. Use only for debugging or emergency situations.",
  min_test_coverage:
    "Minimum percentage of code that must be covered by tests before a task can pass the quality gate.",
  auto_progression:
    "Automatically move tasks to the next phase when quality gates pass. Requires manual review when disabled.",
  guardian_enabled:
    "Guardian monitors task execution and catches errors before they propagate. Recommended to keep enabled.",
}

// Warning messages
const warningMessages = {
  bypass:
    "Gate enforcement is disabled. Quality gates will be logged but not enforced.",
  lowCoverage: "Test coverage below 50% may lead to quality issues.",
  autoNoGuardian:
    "Auto-progression without Guardian may result in unchecked errors.",
}

// Validation errors
interface ValidationErrors {
  min_test_coverage?: string
}

function validateCoverage(value: number): string | undefined {
  if (isNaN(value)) {
    return "Coverage must be a number"
  }
  if (value < 0) {
    return "Coverage cannot be negative"
  }
  if (value > 100) {
    return "Coverage cannot exceed 100%"
  }
  return undefined
}

// Helper component for info tooltips with keyboard support
function InfoTooltip({ content }: { content: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-full p-0.5 text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label="More information"
        >
          <HelpCircle className="h-4 w-4" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-[250px]">
        <p>{content}</p>
      </TooltipContent>
    </Tooltip>
  )
}

// Warning banner component
function WarningBanner({
  message,
  variant = "warning",
}: {
  message: string
  variant?: "warning" | "destructive"
}) {
  return (
    <Alert
      className={cn(
        "py-2",
        variant === "warning"
          ? "border-yellow-500/50 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400"
          : "border-destructive/50 bg-destructive/10"
      )}
    >
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription className="ml-2 text-sm">{message}</AlertDescription>
    </Alert>
  )
}

export function SpecDrivenSettingsPanel({
  open,
  onOpenChange,
  settings: initialSettings,
  onSave,
  isLoading = false,
}: SpecDrivenSettingsPanelProps) {
  // Local form state
  const [localSettings, setLocalSettings] = useState<SpecDrivenSettings>(
    initialSettings ?? defaultSettings
  )
  const [coverageInput, setCoverageInput] = useState<string>(
    String(initialSettings?.min_test_coverage ?? defaultSettings.min_test_coverage)
  )
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({})
  const [isSaving, setIsSaving] = useState(false)
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)

  // Track dirty state
  const isDirty = useMemo(() => {
    const original = initialSettings ?? defaultSettings
    return (
      localSettings.bypass_mode !== original.bypass_mode ||
      localSettings.min_test_coverage !== original.min_test_coverage ||
      localSettings.auto_progression !== original.auto_progression ||
      localSettings.guardian_enabled !== original.guardian_enabled
    )
  }, [localSettings, initialSettings])

  // Check for validation errors
  const hasValidationErrors = useMemo(() => {
    return Object.values(validationErrors).some(Boolean)
  }, [validationErrors])

  // Compute active warnings
  const activeWarnings = useMemo(() => {
    const warnings: string[] = []
    if (localSettings.bypass_mode) {
      warnings.push(warningMessages.bypass)
    }
    if (localSettings.min_test_coverage < 50) {
      warnings.push(warningMessages.lowCoverage)
    }
    if (localSettings.auto_progression && !localSettings.guardian_enabled) {
      warnings.push(warningMessages.autoNoGuardian)
    }
    return warnings
  }, [localSettings])

  // Reset form to initial state
  const resetForm = useCallback(() => {
    const settings = initialSettings ?? defaultSettings
    setLocalSettings(settings)
    setCoverageInput(String(settings.min_test_coverage))
    setValidationErrors({})
  }, [initialSettings])

  // Handle coverage input change with validation
  const handleCoverageInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value
      setCoverageInput(value)

      const numValue = parseFloat(value)
      const error = validateCoverage(numValue)

      setValidationErrors((prev) => ({
        ...prev,
        min_test_coverage: error,
      }))

      if (!error) {
        setLocalSettings((prev) => ({
          ...prev,
          min_test_coverage: numValue,
        }))
      }
    },
    []
  )

  // Handle slider change
  const handleSliderChange = useCallback((values: number[]) => {
    const value = values[0]
    setCoverageInput(String(value))
    setValidationErrors((prev) => ({
      ...prev,
      min_test_coverage: undefined,
    }))
    setLocalSettings((prev) => ({
      ...prev,
      min_test_coverage: value,
    }))
  }, [])

  // Handle switch toggle
  const handleToggle = useCallback(
    (field: keyof SpecDrivenSettings) => (checked: boolean) => {
      setLocalSettings((prev) => ({
        ...prev,
        [field]: checked,
      }))
    },
    []
  )

  // Handle save
  const handleSave = useCallback(async () => {
    if (hasValidationErrors || !onSave) return

    setIsSaving(true)
    try {
      await onSave(localSettings)
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to save settings:", error)
    } finally {
      setIsSaving(false)
    }
  }, [hasValidationErrors, localSettings, onSave, onOpenChange])

  // Handle close with unsaved changes check
  const handleClose = useCallback(() => {
    if (isDirty) {
      setShowUnsavedDialog(true)
    } else {
      onOpenChange(false)
    }
  }, [isDirty, onOpenChange])

  // Handle discard changes
  const handleDiscard = useCallback(() => {
    resetForm()
    setShowUnsavedDialog(false)
    onOpenChange(false)
  }, [resetForm, onOpenChange])

  // Sync local state when initial settings change
  React.useEffect(() => {
    if (initialSettings && open) {
      setLocalSettings(initialSettings)
      setCoverageInput(String(initialSettings.min_test_coverage))
      setValidationErrors({})
    }
  }, [initialSettings, open])

  return (
    <TooltipProvider>
      <Sheet open={open} onOpenChange={handleClose}>
        <SheetContent className="flex flex-col sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Spec-Driven Settings</SheetTitle>
            <SheetDescription>
              Configure quality gates and automation settings for spec-driven
              development.
            </SheetDescription>
          </SheetHeader>

          {/* Warning Banners */}
          {activeWarnings.length > 0 && (
            <div className="space-y-2 mt-4">
              {activeWarnings.map((warning, index) => (
                <WarningBanner
                  key={index}
                  message={warning}
                  variant={
                    warning === warningMessages.bypass ? "destructive" : "warning"
                  }
                />
              ))}
            </div>
          )}

          {/* Settings Form */}
          <div className="flex-1 space-y-6 py-6 overflow-y-auto">
            {/* Bypass Mode */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label htmlFor="bypass-mode" className="font-medium">
                    Bypass Mode
                  </Label>
                  <InfoTooltip content={tooltipDescriptions.bypass_mode} />
                </div>
                <Switch
                  id="bypass-mode"
                  checked={localSettings.bypass_mode}
                  onCheckedChange={handleToggle("bypass_mode")}
                  disabled={isLoading}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Disable quality gate enforcement
              </p>
            </div>

            {/* Min Test Coverage */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Label htmlFor="min-coverage" className="font-medium">
                  Minimum Test Coverage
                </Label>
                <InfoTooltip content={tooltipDescriptions.min_test_coverage} />
              </div>
              <div className="flex items-center gap-4">
                <Slider
                  value={[localSettings.min_test_coverage]}
                  onValueChange={handleSliderChange}
                  min={0}
                  max={100}
                  step={1}
                  className="flex-1"
                  disabled={isLoading}
                />
                <div className="w-20">
                  <Input
                    id="min-coverage"
                    type="number"
                    min={0}
                    max={100}
                    value={coverageInput}
                    onChange={handleCoverageInputChange}
                    className={cn(
                      "h-8 text-center",
                      validationErrors.min_test_coverage &&
                        "border-destructive focus-visible:ring-destructive"
                    )}
                    disabled={isLoading}
                    aria-invalid={!!validationErrors.min_test_coverage}
                    aria-describedby={
                      validationErrors.min_test_coverage
                        ? "coverage-error"
                        : undefined
                    }
                  />
                </div>
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              {validationErrors.min_test_coverage && (
                <p
                  id="coverage-error"
                  className="text-sm text-destructive"
                  role="alert"
                >
                  {validationErrors.min_test_coverage}
                </p>
              )}
            </div>

            {/* Auto Progression */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label htmlFor="auto-progression" className="font-medium">
                    Auto Progression
                  </Label>
                  <InfoTooltip content={tooltipDescriptions.auto_progression} />
                </div>
                <Switch
                  id="auto-progression"
                  checked={localSettings.auto_progression}
                  onCheckedChange={handleToggle("auto_progression")}
                  disabled={isLoading}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Automatically advance tasks through phases
              </p>
            </div>

            {/* Guardian Enabled */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label htmlFor="guardian-enabled" className="font-medium">
                    Guardian
                  </Label>
                  <InfoTooltip content={tooltipDescriptions.guardian_enabled} />
                </div>
                <Switch
                  id="guardian-enabled"
                  checked={localSettings.guardian_enabled}
                  onCheckedChange={handleToggle("guardian_enabled")}
                  disabled={isLoading}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Enable error monitoring and prevention
              </p>
            </div>
          </div>

          {/* Footer with actions */}
          <SheetFooter className="flex-shrink-0 border-t pt-4">
            <div className="flex w-full gap-2">
              <Button
                variant="outline"
                onClick={resetForm}
                disabled={!isDirty || isLoading || isSaving}
                className="flex-1"
              >
                Reset
              </Button>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={isSaving}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={!isDirty || hasValidationErrors || isLoading || isSaving}
                className="flex-1"
              >
                {isSaving ? "Saving..." : "Save"}
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Unsaved Changes Dialog */}
      <AlertDialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to discard them?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continue Editing</AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscard}>
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </TooltipProvider>
  )
}
