"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Check,
  Crown,
  Zap,
  Infinity,
  ArrowRight,
  Loader2,
  Sparkles,
  Clock,
} from "lucide-react"
import { useOnboarding } from "@/hooks/useOnboarding"
import { cn } from "@/lib/utils"
import { useCreateLifetimeCheckout, useStripeConfig } from "@/hooks/useBilling"
import { useToast } from "@/hooks/use-toast"

interface PlanOption {
  id: string
  name: string
  price: string
  priceNote?: string
  icon: React.ReactNode
  features: string[]
  highlighted?: boolean
  urgencyText?: string
  accentColor: string
}

const PLANS: PlanOption[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    priceNote: "forever",
    icon: <Zap className="h-5 w-5" />,
    features: [
      "1 concurrent agent",
      "5 workflows/month",
      "2GB storage",
      "Community support",
    ],
    accentColor: "bg-slate-500",
  },
  {
    id: "pro",
    name: "Pro",
    price: "$50",
    priceNote: "/month",
    icon: <Crown className="h-5 w-5" />,
    features: [
      "5 concurrent agents",
      "100 workflows/month",
      "50GB storage",
      "BYO API keys",
      "Priority support",
    ],
    accentColor: "bg-purple-500",
  },
  {
    id: "lifetime",
    name: "Founding Member",
    price: "$299",
    priceNote: "one-time",
    icon: <Infinity className="h-5 w-5" />,
    features: [
      "5 concurrent agents",
      "50 workflows/month",
      "50GB storage",
      "BYO API keys",
      "Lifetime access",
      "Early feature access",
    ],
    highlighted: true,
    urgencyText: "Only 87 spots left!",
    accentColor: "bg-emerald-500",
  },
]

export function PlanSelectStep() {
  const { data, updateData, nextStep, isLoading: onboardingLoading } = useOnboarding()
  const { toast } = useToast()
  const [selectedPlan, setSelectedPlan] = useState<string>(data.selectedPlan || "free")
  const [isProcessing, setIsProcessing] = useState(false)

  const createLifetimeCheckout = useCreateLifetimeCheckout()
  const { data: stripeConfig } = useStripeConfig()

  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId)
    updateData({ selectedPlan: planId })
  }

  const handleContinue = async () => {
    if (selectedPlan === "free") {
      // Skip payment, go to complete
      nextStep()
      return
    }

    if (selectedPlan === "lifetime") {
      // Start Stripe checkout for lifetime
      setIsProcessing(true)
      try {
        // Need org ID - use the one from onboarding or create one
        const orgId = data.organizationId
        if (!orgId) {
          toast({
            title: "Setup incomplete",
            description: "Please complete the previous steps first.",
            variant: "destructive",
          })
          return
        }

        const result = await createLifetimeCheckout.mutateAsync({ orgId })
        window.location.href = result.checkout_url
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to start checkout. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsProcessing(false)
      }
      return
    }

    if (selectedPlan === "pro") {
      // For now, skip to complete and show billing later
      // In production, this would start a Stripe subscription checkout
      toast({
        title: "Coming soon",
        description: "Pro subscriptions will be available shortly. Continuing with free tier.",
      })
      updateData({ selectedPlan: "free" })
      nextStep()
      return
    }
  }

  const handleSkip = () => {
    updateData({ selectedPlan: "free" })
    nextStep()
  }

  const isLoading = onboardingLoading || isProcessing || createLifetimeCheckout.isPending

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <div className="h-8 w-8 rounded-full bg-green-500/10 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-green-600" />
          </div>
          <CardTitle className="text-2xl">Your First Agent is Working!</CardTitle>
        </div>
        <CardDescription>
          While it runs, check out what&apos;s possible with more power:
        </CardDescription>
      </div>

      {/* Agent progress indicator */}
      {data.firstSpecText && (
        <div className="p-3 rounded-lg bg-muted/50 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4 animate-pulse text-primary" />
            <span>Working on: &quot;{data.firstSpecText.slice(0, 40)}...&quot;</span>
          </div>
        </div>
      )}

      {/* Plan cards */}
      <div className="space-y-3">
        {PLANS.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            isSelected={selectedPlan === plan.id}
            onSelect={() => handleSelectPlan(plan.id)}
            disabled={isLoading}
          />
        ))}
      </div>

      {/* Action buttons */}
      <div className="space-y-3">
        <Button
          size="lg"
          onClick={handleContinue}
          disabled={isLoading}
          className={cn(
            "w-full",
            selectedPlan === "lifetime" && "bg-emerald-600 hover:bg-emerald-700"
          )}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Processing...
            </>
          ) : selectedPlan === "free" ? (
            <>
              Continue with Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          ) : selectedPlan === "lifetime" ? (
            <>
              Claim Founding Member Access
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          ) : (
            <>
              Upgrade to {PLANS.find(p => p.id === selectedPlan)?.name}
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          )}
        </Button>

        {selectedPlan !== "free" && (
          <Button
            variant="ghost"
            onClick={handleSkip}
            disabled={isLoading}
            className="w-full text-muted-foreground"
          >
            Skip for now - Continue to Dashboard
          </Button>
        )}
      </div>
    </div>
  )
}

function PlanCard({
  plan,
  isSelected,
  onSelect,
  disabled,
}: {
  plan: PlanOption
  isSelected: boolean
  onSelect: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className={cn(
        "relative w-full text-left rounded-lg border p-4 transition-all",
        "hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
        isSelected && "border-primary bg-primary/5 ring-1 ring-primary",
        plan.highlighted && !isSelected && "border-emerald-500/30",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      {/* Highlight badge */}
      {plan.highlighted && (
        <Badge className="absolute -top-2 right-2 bg-emerald-500 text-white text-xs px-2 py-0">
          Best Value
        </Badge>
      )}

      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            plan.id === "free" && "bg-slate-500/10 text-slate-500",
            plan.id === "pro" && "bg-purple-500/10 text-purple-500",
            plan.id === "lifetime" && "bg-emerald-500/10 text-emerald-500"
          )}
        >
          {plan.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{plan.name}</h3>
            <div className="text-right">
              <span className="font-bold text-lg">{plan.price}</span>
              {plan.priceNote && (
                <span className="text-sm text-muted-foreground ml-1">{plan.priceNote}</span>
              )}
            </div>
          </div>

          {/* Features */}
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {plan.features.slice(0, 4).map((feature) => (
              <span key={feature} className="flex items-center gap-1">
                <Check className="h-3 w-3 text-primary" />
                {feature}
              </span>
            ))}
          </div>

          {/* Urgency text */}
          {plan.urgencyText && (
            <p className="mt-2 text-xs font-medium text-emerald-600">
              {plan.urgencyText}
            </p>
          )}
        </div>

        {/* Selection indicator */}
        <div
          className={cn(
            "w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-all",
            isSelected ? "border-primary bg-primary" : "border-muted-foreground/30"
          )}
        >
          {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
        </div>
      </div>
    </button>
  )
}
