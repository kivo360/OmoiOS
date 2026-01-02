"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Check,
  Crown,
  Zap,
  Users,
  Infinity,
  ArrowRight,
  Sparkles,
} from "lucide-react"
import type { SubscriptionTier } from "@/lib/api/types"
import { TIER_CONFIGS } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface PricingTableProps {
  currentTier?: SubscriptionTier
  onSelectTier: (tier: SubscriptionTier) => void
  isLoading?: boolean
  showLifetime?: boolean
  showEnterprise?: boolean
  compact?: boolean
  className?: string
}

const tierIcons: Record<SubscriptionTier, React.ReactNode> = {
  free: <Zap className="h-5 w-5" />,
  pro: <Crown className="h-5 w-5" />,
  team: <Users className="h-5 w-5" />,
  enterprise: <Crown className="h-5 w-5" />,
  lifetime: <Infinity className="h-5 w-5" />,
}

const tierOrder: SubscriptionTier[] = ["free", "pro", "team"]
const specialTiers: SubscriptionTier[] = ["lifetime", "enterprise"]

function PricingCard({
  tier,
  currentTier,
  onSelect,
  isLoading,
  compact,
}: {
  tier: SubscriptionTier
  currentTier?: SubscriptionTier
  onSelect: (tier: SubscriptionTier) => void
  isLoading?: boolean
  compact?: boolean
}) {
  const config = TIER_CONFIGS[tier]
  const isCurrent = currentTier === tier
  const isHighlighted = config.highlighted
  const isDowngrade = currentTier && tierOrder.indexOf(tier) < tierOrder.indexOf(currentTier)
  const isSpecial = specialTiers.includes(tier)

  const getButtonLabel = () => {
    if (isCurrent) return "Current Plan"
    if (tier === "enterprise") return "Contact Sales"
    if (tier === "lifetime") return "Claim Lifetime Access"
    if (isDowngrade) return "Downgrade"
    return config.ctaLabel
  }

  const getButtonVariant = (): "default" | "outline" | "secondary" => {
    if (isCurrent) return "secondary"
    if (isHighlighted) return "default"
    return "outline"
  }

  return (
    <Card
      className={cn(
        "relative flex flex-col",
        isHighlighted && "border-primary shadow-lg ring-1 ring-primary",
        isCurrent && "border-green-500/50 bg-green-500/5",
        compact && "p-2"
      )}
    >
      {isHighlighted && !isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge className="bg-primary text-primary-foreground px-3">
            <Sparkles className="mr-1 h-3 w-3" />
            Most Popular
          </Badge>
        </div>
      )}
      {isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30 px-3">
            <Check className="mr-1 h-3 w-3" />
            Current Plan
          </Badge>
        </div>
      )}

      <CardHeader className={cn(compact && "p-4 pb-2")}>
        <div className="flex items-center gap-2">
          <div className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            tier === "pro" && "bg-purple-500/10 text-purple-500",
            tier === "team" && "bg-indigo-500/10 text-indigo-500",
            tier === "enterprise" && "bg-amber-500/10 text-amber-500",
            tier === "lifetime" && "bg-emerald-500/10 text-emerald-500",
            tier === "free" && "bg-slate-500/10 text-slate-500",
          )}>
            {tierIcons[tier]}
          </div>
          <div>
            <CardTitle className="text-lg">{config.displayName}</CardTitle>
          </div>
        </div>
        <div className="mt-4">
          <span className="text-3xl font-bold">
            {config.price === 0 && tier !== "enterprise" ? "$0" :
             tier === "enterprise" ? "Custom" :
             `$${config.price}`}
          </span>
          <span className="text-muted-foreground">
            {tier === "lifetime" ? " one-time" :
             tier === "enterprise" ? "" :
             "/month"}
          </span>
        </div>
        <CardDescription className="mt-2">
          {config.workflowsLabel}
        </CardDescription>
      </CardHeader>

      <CardContent className={cn("flex-1 flex flex-col", compact && "p-4 pt-0")}>
        <ul className={cn("space-y-2 flex-1", compact && "text-sm")}>
          {config.features.map((feature, index) => (
            <li key={index} className="flex items-start gap-2">
              <Check className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <span className="text-muted-foreground">{feature}</span>
            </li>
          ))}
        </ul>

        <Button
          variant={getButtonVariant()}
          className={cn(
            "w-full mt-6",
            isHighlighted && !isCurrent && "bg-primary hover:bg-primary/90"
          )}
          disabled={isCurrent || isLoading}
          onClick={() => onSelect(tier)}
        >
          {getButtonLabel()}
          {!isCurrent && !isSpecial && <ArrowRight className="ml-2 h-4 w-4" />}
        </Button>
      </CardContent>
    </Card>
  )
}

function SpecialOfferCard({
  tier,
  currentTier,
  onSelect,
  isLoading,
}: {
  tier: "lifetime"
  currentTier?: SubscriptionTier
  onSelect: (tier: SubscriptionTier) => void
  isLoading?: boolean
}) {
  const config = TIER_CONFIGS[tier]
  const isCurrent = currentTier === tier

  return (
    <Card className={cn(
      "relative border-emerald-500/30 bg-gradient-to-br from-emerald-500/5 to-transparent",
      isCurrent && "ring-2 ring-green-500/50"
    )}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
              {tierIcons[tier]}
            </div>
            <div>
              <CardTitle>{config.displayName}</CardTitle>
              <CardDescription>{config.priceLabel}</CardDescription>
            </div>
          </div>
          {isCurrent && (
            <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30">
              Current
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Pay once, use forever. Perfect for indie developers and small teams who want predictable costs.
        </p>
        <div className="flex flex-wrap gap-2 mb-4">
          {config.features.slice(0, 4).map((feature: string, index: number) => (
            <Badge key={index} variant="secondary" className="font-normal">
              {feature}
            </Badge>
          ))}
        </div>
        <Button
          variant={isCurrent ? "secondary" : "outline"}
          className="w-full"
          disabled={isCurrent || isLoading}
          onClick={() => onSelect(tier)}
        >
          {isCurrent ? "Current Plan" : config.ctaLabel}
        </Button>
      </CardContent>
    </Card>
  )
}

export function PricingTable({
  currentTier,
  onSelectTier,
  isLoading,
  showLifetime = true,
  showEnterprise = true,
  compact = false,
  className,
}: PricingTableProps) {
  // Filter tiers to show
  const mainTiers = tierOrder.filter((tier) => {
    if (tier === "enterprise" && !showEnterprise) return false
    return true
  })

  return (
    <div className={cn("space-y-8", className)}>
      {/* Main pricing grid */}
      <div className={cn(
        "grid gap-4",
        compact ? "grid-cols-2 lg:grid-cols-3" : "grid-cols-1 md:grid-cols-3"
      )}>
        {mainTiers.map((tier) => (
          <PricingCard
            key={tier}
            tier={tier}
            currentTier={currentTier}
            onSelect={onSelectTier}
            isLoading={isLoading}
            compact={compact}
          />
        ))}
      </div>

      {/* Special offers section */}
      {showLifetime && (
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold">Special Options</h3>
            <p className="text-sm text-muted-foreground">
              Alternative plans for unique needs
            </p>
          </div>
          <div className="max-w-lg mx-auto">
            <SpecialOfferCard
              tier="lifetime"
              currentTier={currentTier}
              onSelect={onSelectTier}
              isLoading={isLoading}
            />
          </div>
        </div>
      )}

      {/* Enterprise CTA */}
      {showEnterprise && (
        <Card className="bg-gradient-to-r from-amber-500/5 via-transparent to-amber-500/5 border-amber-500/20">
          <CardContent className="flex flex-col md:flex-row items-center justify-between gap-4 p-6">
            <div className="flex items-center gap-4 text-center md:text-left">
              <div className="hidden md:flex h-12 w-12 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
                <Crown className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold">Need more? Go Enterprise</h3>
                <p className="text-sm text-muted-foreground">
                  Unlimited everything, custom integrations, SLA, and dedicated support.
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              className="border-amber-500/30 hover:bg-amber-500/10"
              onClick={() => onSelectTier("enterprise")}
            >
              Contact Sales
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
