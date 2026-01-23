"use client"

import * as React from "react"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

export type GateEnforcementStrictness = "bypass" | "lenient" | "strict"

export interface SpecDrivenSettings {
  auto_phase_progression: boolean
  gate_enforcement_strictness: GateEnforcementStrictness
  min_test_coverage: number
  guardian_auto_steering: boolean
}

const DEFAULT_SETTINGS: SpecDrivenSettings = {
  auto_phase_progression: true,
  gate_enforcement_strictness: "lenient",
  min_test_coverage: 80,
  guardian_auto_steering: true,
}

const GATE_ENFORCEMENT_OPTIONS: {
  value: GateEnforcementStrictness
  label: string
  description: string
}[] = [
  {
    value: "bypass",
    label: "Bypass",
    description: "Skip all gate checks and proceed freely",
  },
  {
    value: "lenient",
    label: "Lenient",
    description: "Warn on gate failures but allow progression",
  },
  {
    value: "strict",
    label: "Strict",
    description: "Block progression until all gates pass",
  },
]

interface SpecDrivenSettingsPanelProps {
  settings?: SpecDrivenSettings
  onChange?: (settings: SpecDrivenSettings) => void
  className?: string
}

export function SpecDrivenSettingsPanel({
  settings: externalSettings,
  onChange,
  className,
}: SpecDrivenSettingsPanelProps) {
  const [localSettings, setLocalSettings] = React.useState<SpecDrivenSettings>(
    externalSettings ?? DEFAULT_SETTINGS
  )

  // Sync with external settings when they change
  React.useEffect(() => {
    if (externalSettings) {
      setLocalSettings(externalSettings)
    }
  }, [externalSettings])

  const updateSetting = <K extends keyof SpecDrivenSettings>(
    key: K,
    value: SpecDrivenSettings[K]
  ) => {
    const newSettings = { ...localSettings, [key]: value }
    setLocalSettings(newSettings)
    onChange?.(newSettings)
  }

  const isCoverageDisabled = localSettings.gate_enforcement_strictness === "bypass"

  return (
    <div className={cn("space-y-6", className)}>
      {/* Auto Phase Progression */}
      <div className="flex items-center justify-between space-x-4">
        <div className="space-y-0.5">
          <Label
            htmlFor="auto-phase-progression"
            className="text-sm font-medium"
          >
            Auto Phase Progression
          </Label>
          <p className="text-sm text-muted-foreground">
            Automatically advance through phases when gates pass
          </p>
        </div>
        <Switch
          id="auto-phase-progression"
          checked={localSettings.auto_phase_progression}
          onCheckedChange={(checked) =>
            updateSetting("auto_phase_progression", checked)
          }
        />
      </div>

      {/* Gate Enforcement Strictness */}
      <div className="space-y-3">
        <div className="space-y-0.5">
          <Label className="text-sm font-medium">Gate Enforcement</Label>
          <p className="text-sm text-muted-foreground">
            Control how strictly phase gates are enforced
          </p>
        </div>
        <RadioGroup
          value={localSettings.gate_enforcement_strictness}
          onValueChange={(value) =>
            updateSetting(
              "gate_enforcement_strictness",
              value as GateEnforcementStrictness
            )
          }
          className="space-y-2"
        >
          {GATE_ENFORCEMENT_OPTIONS.map((option) => (
            <div
              key={option.value}
              className="flex items-start space-x-3 rounded-md border p-3"
            >
              <RadioGroupItem
                value={option.value}
                id={`gate-${option.value}`}
                className="mt-0.5"
              />
              <div className="space-y-1">
                <Label
                  htmlFor={`gate-${option.value}`}
                  className="text-sm font-medium cursor-pointer"
                >
                  {option.label}
                </Label>
                <p className="text-sm text-muted-foreground">
                  {option.description}
                </p>
              </div>
            </div>
          ))}
        </RadioGroup>
      </div>

      {/* Min Test Coverage */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label
              htmlFor="min-test-coverage"
              className={cn(
                "text-sm font-medium",
                isCoverageDisabled && "text-muted-foreground"
              )}
            >
              Minimum Test Coverage
            </Label>
            <p className="text-sm text-muted-foreground">
              Required test coverage percentage for gate checks
            </p>
          </div>
          <span
            className={cn(
              "text-sm font-medium tabular-nums",
              isCoverageDisabled && "text-muted-foreground"
            )}
          >
            {localSettings.min_test_coverage}%
          </span>
        </div>
        <Slider
          id="min-test-coverage"
          min={0}
          max={100}
          step={1}
          value={[localSettings.min_test_coverage]}
          onValueChange={(value) => updateSetting("min_test_coverage", value[0])}
          disabled={isCoverageDisabled}
          className={cn(isCoverageDisabled && "opacity-50")}
        />
        {isCoverageDisabled && (
          <p className="text-xs text-muted-foreground">
            Coverage checks are disabled when gate enforcement is set to bypass
          </p>
        )}
      </div>

      {/* Guardian Auto-Steering */}
      <div className="flex items-center justify-between space-x-4">
        <div className="space-y-0.5">
          <Label
            htmlFor="guardian-auto-steering"
            className="text-sm font-medium"
          >
            Guardian Auto-Steering
          </Label>
          <p className="text-sm text-muted-foreground">
            Enable automatic interventions by the guardian system
          </p>
        </div>
        <Switch
          id="guardian-auto-steering"
          checked={localSettings.guardian_auto_steering}
          onCheckedChange={(checked) =>
            updateSetting("guardian_auto_steering", checked)
          }
        />
      </div>
    </div>
  )
}
