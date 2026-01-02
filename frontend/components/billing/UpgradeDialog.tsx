"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Check,
  Crown,
  Zap,
  Users,
  Infinity,
  Key,
  ArrowRight,
  Loader2,
  AlertCircle,
  Sparkles,
} from "lucide-react"
import type { SubscriptionTier } from "@/lib/api/types"
import { TIER_CONFIGS } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface UpgradeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentTier?: SubscriptionTier
  onSelectTier: (tier: SubscriptionTier) => Promise<void>
  isLoading?: boolean
  error?: string | null
}

const tierIcons: Record<SubscriptionTier, React.ReactNode> = {
  free: <Zap className="h-5 w-5" />,
  pro: <Crown className="h-5 w-5" />,
  team: <Users className="h-5 w-5" />,
  enterprise: <Crown className="h-5 w-5" />,
  lifetime: <Infinity className="h-5 w-5" />,
}

const tierColors: Record<SubscriptionTier, string> = {
  free: "bg-slate-500/10 text-slate-500",
  pro: "bg-purple-500/10 text-purple-500",
  team: "bg-indigo-500/10 text-indigo-500",
  enterprise: "bg-amber-500/10 text-amber-500",
  lifetime: "bg-emerald-500/10 text-emerald-500",
}

const monthlyTiers: SubscriptionTier[] = ["pro", "team"]
const specialTiers: SubscriptionTier[] = ["lifetime"]

function TierOption({
  tier,
  currentTier,
  selectedTier,
  onSelect,
  compact = false,
}: {
  tier: SubscriptionTier
  currentTier?: SubscriptionTier
  selectedTier: SubscriptionTier | null
  onSelect: (tier: SubscriptionTier) => void
  compact?: boolean
}) {
  const config = TIER_CONFIGS[tier]
  const isCurrent = currentTier === tier
  const isSelected = selectedTier === tier
  const isHighlighted = config.highlighted

  return (
    <button
      type="button"
      onClick={() => !isCurrent && onSelect(tier)}
      disabled={isCurrent}
      className={cn(
        "relative w-full text-left rounded-lg border p-4 transition-all",
        "hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
        isSelected && "border-primary bg-primary/5 ring-1 ring-primary",
        isCurrent && "opacity-50 cursor-not-allowed",
        isHighlighted && !isSelected && "border-purple-500/30",
        compact && "p-3"
      )}
    >
      {isHighlighted && !isCurrent && (
        <Badge className="absolute -top-2 right-2 bg-purple-500 text-white text-xs px-2 py-0">
          Popular
        </Badge>
      )}
      {isCurrent && (
        <Badge variant="secondary" className="absolute -top-2 right-2 text-xs px-2 py-0">
          Current
        </Badge>
      )}

      <div className="flex items-start gap-3">
        <div className={cn(
          "flex h-10 w-10 items-center justify-center rounded-lg shrink-0",
          tierColors[tier]
        )}>
          {tierIcons[tier]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold">{config.displayName}</h3>
            <span className="font-bold text-lg">
              {tier === "lifetime" ? `$${config.price}` : `$${config.price}/mo`}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {config.workflowsLabel}
          </p>
          {!compact && (
            <div className="flex flex-wrap gap-1 mt-2">
              {config.features.slice(0, 3).map((feature, idx) => (
                <Badge key={idx} variant="outline" className="text-xs font-normal">
                  {feature}
                </Badge>
              ))}
            </div>
          )}
        </div>
        <div className={cn(
          "w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-all",
          isSelected ? "border-primary bg-primary" : "border-muted-foreground/30"
        )}>
          {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
        </div>
      </div>
    </button>
  )
}

function ComparisonView({
  currentTier,
  selectedTier,
}: {
  currentTier?: SubscriptionTier
  selectedTier: SubscriptionTier | null
}) {
  if (!selectedTier || !currentTier || selectedTier === currentTier) return null

  const current = TIER_CONFIGS[currentTier]
  const selected = TIER_CONFIGS[selectedTier]

  const comparisons = [
    {
      label: "Workflows/month",
      current: current.workflows === -1 ? "Unlimited" : current.workflows,
      new: selected.workflows === -1 ? "Unlimited" : selected.workflows,
    },
    {
      label: "Concurrent Agents",
      current: current.agents === -1 ? "Unlimited" : current.agents,
      new: selected.agents === -1 ? "Unlimited" : selected.agents,
    },
    {
      label: "Storage",
      current: current.storageGb === -1 ? "Unlimited" : `${current.storageGb}GB`,
      new: selected.storageGb === -1 ? "Unlimited" : `${selected.storageGb}GB`,
    },
  ]

  return (
    <div className="mt-4 p-4 rounded-lg bg-muted/50 space-y-3">
      <h4 className="font-medium text-sm flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-primary" />
        What you'll get
      </h4>
      <div className="space-y-2">
        {comparisons.map((item) => (
          <div key={item.label} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{item.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground line-through">{item.current}</span>
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <span className="font-medium text-primary">{item.new}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function UpgradeDialog({
  open,
  onOpenChange,
  currentTier,
  onSelectTier,
  isLoading,
  error,
}: UpgradeDialogProps) {
  const [selectedTier, setSelectedTier] = useState<SubscriptionTier | null>(null)
  const [activeTab, setActiveTab] = useState<"monthly" | "special">("monthly")

  const handleConfirm = async () => {
    if (!selectedTier) return
    await onSelectTier(selectedTier)
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedTier(null)
    }
    onOpenChange(newOpen)
  }

  const getConfirmButtonText = () => {
    if (!selectedTier) return "Select a plan"
    if (selectedTier === "enterprise") return "Contact Sales"
    if (selectedTier === "lifetime") return "Proceed to Checkout"
    return `Upgrade to ${TIER_CONFIGS[selectedTier].displayName}`
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">
            {currentTier === "free" ? "Upgrade Your Plan" : "Change Your Plan"}
          </DialogTitle>
          <DialogDescription>
            Choose the plan that best fits your needs. You can upgrade, downgrade, or switch plans at any time.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "monthly" | "special")} className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="monthly">Monthly Plans</TabsTrigger>
            <TabsTrigger value="special">Special Offers</TabsTrigger>
          </TabsList>

          <TabsContent value="monthly" className="mt-4 space-y-3">
            {/* Free tier - show only if currently free */}
            {currentTier === "free" && (
              <TierOption
                tier="free"
                currentTier={currentTier}
                selectedTier={selectedTier}
                onSelect={setSelectedTier}
              />
            )}

            {/* Monthly subscription tiers */}
            {monthlyTiers.map((tier) => (
              <TierOption
                key={tier}
                tier={tier}
                currentTier={currentTier}
                selectedTier={selectedTier}
                onSelect={setSelectedTier}
              />
            ))}

            {/* Enterprise teaser */}
            <button
              type="button"
              onClick={() => setSelectedTier("enterprise")}
              className={cn(
                "w-full text-left rounded-lg border border-dashed border-amber-500/30 p-4",
                "bg-gradient-to-r from-amber-500/5 to-transparent",
                "hover:border-amber-500/50 transition-all",
                selectedTier === "enterprise" && "border-amber-500 ring-1 ring-amber-500"
              )}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
                  <Crown className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold">Enterprise</h3>
                  <p className="text-sm text-muted-foreground">
                    Custom pricing for unlimited everything
                  </p>
                </div>
                <ArrowRight className="h-5 w-5 text-amber-500" />
              </div>
            </button>
          </TabsContent>

          <TabsContent value="special" className="mt-4 space-y-3">
            {specialTiers.map((tier) => (
              <TierOption
                key={tier}
                tier={tier}
                currentTier={currentTier}
                selectedTier={selectedTier}
                onSelect={setSelectedTier}
              />
            ))}

            <div className="p-4 rounded-lg bg-muted/50 text-sm text-muted-foreground">
              <p className="font-medium mb-2">About Special Plans</p>
              <ul className="space-y-1">
                <li className="flex items-start gap-2">
                  <Infinity className="h-4 w-4 mt-0.5 text-emerald-500" />
                  <span><strong>Lifetime:</strong> One-time payment of $299, no recurring charges. 50 workflows/month, 5 agents, and BYO API keys.</span>
                </li>
              </ul>
              <p className="mt-3 text-xs">
                <Key className="inline h-3 w-3 mr-1" />
                <strong>BYO API Keys</strong> is included with Pro, Team, and Lifetime plans.
              </p>
            </div>
          </TabsContent>
        </Tabs>

        {/* Comparison view */}
        <ComparisonView currentTier={currentTier} selectedTier={selectedTier} />

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            className="flex-1"
            onClick={handleConfirm}
            disabled={!selectedTier || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              getConfirmButtonText()
            )}
          </Button>
        </div>

        {/* Billing note */}
        {selectedTier && selectedTier !== "enterprise" && selectedTier !== currentTier && (
          <p className="text-xs text-center text-muted-foreground mt-2">
            {selectedTier === "lifetime"
              ? "You'll be redirected to Stripe for a one-time payment."
              : "You'll be redirected to Stripe to complete your subscription."}
          </p>
        )}
      </DialogContent>
    </Dialog>
  )
}
