"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Crown,
  Zap,
  Users,
  HardDrive,
  Calendar,
  Infinity,
  AlertTriangle,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";
import type {
  Subscription,
  SubscriptionTier,
  SubscriptionStatus,
} from "@/lib/api/types";
import { TIER_CONFIGS } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface SubscriptionCardProps {
  subscription: Subscription | null | undefined;
  isLoading?: boolean;
  onUpgrade?: () => void;
  onManage?: () => void;
  onCancel?: () => void;
  onReactivate?: () => void;
  className?: string;
}

const statusConfig: Record<
  SubscriptionStatus,
  {
    label: string;
    variant: "default" | "secondary" | "destructive" | "outline";
  }
> = {
  active: { label: "Active", variant: "default" },
  trialing: { label: "Trial", variant: "secondary" },
  past_due: { label: "Past Due", variant: "destructive" },
  canceled: { label: "Canceled", variant: "destructive" },
  paused: { label: "Paused", variant: "secondary" },
  incomplete: { label: "Incomplete", variant: "outline" },
};

const tierIcons: Record<SubscriptionTier, React.ReactNode> = {
  free: <Zap className="h-5 w-5" />,
  pro: <Crown className="h-5 w-5" />,
  team: <Users className="h-5 w-5" />,
  enterprise: <Crown className="h-5 w-5" />,
  lifetime: <Infinity className="h-5 w-5" />,
};

const tierColors: Record<SubscriptionTier, string> = {
  free: "bg-slate-500/10 text-slate-500",
  pro: "bg-purple-500/10 text-purple-500",
  team: "bg-indigo-500/10 text-indigo-500",
  enterprise: "bg-amber-500/10 text-amber-500",
  lifetime: "bg-emerald-500/10 text-emerald-500",
};

function UsageMeter({
  label,
  icon,
  used,
  limit,
  unit = "",
  unlimited = false,
}: {
  label: string;
  icon: React.ReactNode;
  used: number;
  limit: number;
  unit?: string;
  unlimited?: boolean;
}) {
  const percentage = unlimited
    ? 0
    : limit > 0
      ? Math.min((used / limit) * 100, 100)
      : 0;
  const isNearLimit = percentage >= 80 && percentage < 100;
  const isAtLimit = percentage >= 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span>{label}</span>
        </div>
        <span
          className={cn(
            "font-medium",
            isAtLimit && "text-destructive",
            isNearLimit && "text-warning",
          )}
        >
          {unlimited ? (
            <span className="flex items-center gap-1">
              <Infinity className="h-3 w-3" />
              Unlimited
            </span>
          ) : (
            `${used}${unit} / ${limit}${unit}`
          )}
        </span>
      </div>
      {!unlimited && (
        <Progress
          value={percentage}
          className={cn(
            "h-2",
            isAtLimit && "[&>div]:bg-destructive",
            isNearLimit && "[&>div]:bg-warning",
          )}
        />
      )}
    </div>
  );
}

export function SubscriptionCard({
  subscription,
  isLoading,
  onUpgrade,
  onManage,
  onCancel,
  onReactivate,
  className,
}: SubscriptionCardProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-4 w-48" />
            </div>
            <Skeleton className="h-8 w-20" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-2 w-full" />
              </div>
            ))}
          </div>
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  // Default to free tier if no subscription
  const tier = subscription?.tier || "free";
  const status = subscription?.status || "active";
  const tierConfig = TIER_CONFIGS[tier];
  const statusInfo = statusConfig[status];

  const workflowsUsed = subscription?.workflows_used || 0;
  const workflowsLimit = subscription?.workflows_limit || tierConfig.workflows;
  const agentsLimit = subscription?.agents_limit || tierConfig.agents;
  const storageUsed = subscription?.storage_used_gb || 0;
  const storageLimit = subscription?.storage_limit_gb || tierConfig.storageGb;

  const isLifetime = subscription?.is_lifetime || tier === "lifetime";
  const isBYO = subscription?.is_byo;
  const isUnlimited = tier === "enterprise" || workflowsLimit === -1;
  const isCanceled = status === "canceled";
  const cancelAtPeriodEnd = subscription?.cancel_at_period_end;

  // Format renewal/expiry date
  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end)
    : null;

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <Card className={cn("relative overflow-hidden", className)}>
      {/* Tier accent bar */}
      <div
        className={cn(
          "absolute top-0 left-0 right-0 h-1",
          tier === "pro" && "bg-purple-500",
          tier === "team" && "bg-indigo-500",
          tier === "enterprise" && "bg-amber-500",
          tier === "lifetime" && "bg-emerald-500",
          tier === "free" && "bg-slate-500",
        )}
      />

      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  tierColors[tier],
                )}
              >
                {tierIcons[tier]}
              </div>
              <div>
                <CardTitle className="flex items-center gap-2">
                  {tierConfig.displayName}
                  {isLifetime && (
                    <Badge
                      variant="outline"
                      className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                    >
                      Lifetime
                    </Badge>
                  )}
                  {isBYO && (
                    <Badge
                      variant="outline"
                      className="bg-cyan-500/10 text-cyan-600 border-cyan-500/20"
                    >
                      BYO Keys
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>{tierConfig.priceLabel}</CardDescription>
              </div>
            </div>
          </div>
          <Badge variant={statusInfo.variant}>
            {cancelAtPeriodEnd && status === "active"
              ? "Canceling"
              : statusInfo.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Warning for canceled/past due */}
        {(isCanceled || status === "past_due" || cancelAtPeriodEnd) && (
          <div
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg",
              status === "past_due" ? "bg-destructive/10" : "bg-warning/10",
            )}
          >
            <AlertTriangle
              className={cn(
                "h-5 w-5 mt-0.5",
                status === "past_due" ? "text-destructive" : "text-warning",
              )}
            />
            <div className="text-sm">
              {status === "past_due" && (
                <>
                  <p className="font-medium text-destructive">
                    Payment Past Due
                  </p>
                  <p className="text-muted-foreground">
                    Please update your payment method to continue using the
                    service.
                  </p>
                </>
              )}
              {cancelAtPeriodEnd && status === "active" && periodEnd && (
                <>
                  <p className="font-medium text-warning">
                    Subscription Ending
                  </p>
                  <p className="text-muted-foreground">
                    Your subscription will end on {formatDate(periodEnd)}. You
                    can reactivate to keep your plan.
                  </p>
                </>
              )}
              {isCanceled && (
                <>
                  <p className="font-medium text-destructive">
                    Subscription Canceled
                  </p>
                  <p className="text-muted-foreground">
                    Your subscription has been canceled. Upgrade to restore
                    access.
                  </p>
                </>
              )}
            </div>
          </div>
        )}

        {/* Usage meters */}
        <div className="space-y-4">
          <UsageMeter
            label="Workflows"
            icon={<Zap className="h-4 w-4" />}
            used={workflowsUsed}
            limit={workflowsLimit}
            unlimited={isUnlimited}
          />
          <UsageMeter
            label="Concurrent Agents"
            icon={<Users className="h-4 w-4" />}
            used={0} // Current active - could be passed in
            limit={agentsLimit}
            unlimited={agentsLimit === -1}
          />
          <UsageMeter
            label="Storage"
            icon={<HardDrive className="h-4 w-4" />}
            used={storageUsed}
            limit={storageLimit}
            unit="GB"
            unlimited={storageLimit === -1}
          />
        </div>

        {/* Renewal/Lifetime info */}
        {!isCanceled && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            {isLifetime ? (
              <span>
                Lifetime access since{" "}
                {subscription?.lifetime_purchase_date
                  ? formatDate(new Date(subscription.lifetime_purchase_date))
                  : "purchase"}
              </span>
            ) : periodEnd ? (
              <span>
                {cancelAtPeriodEnd ? "Ends" : "Renews"} on{" "}
                {formatDate(periodEnd)}
              </span>
            ) : tier === "free" ? (
              <span>Free tier - no renewal needed</span>
            ) : null}
          </div>
        )}

        {/* BYO providers */}
        {isBYO &&
          subscription?.byo_providers_configured &&
          subscription.byo_providers_configured.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Configured Providers
              </p>
              <div className="flex flex-wrap gap-2">
                {subscription.byo_providers_configured.map((provider) => (
                  <Badge
                    key={provider}
                    variant="outline"
                    className="bg-cyan-500/10"
                  >
                    {provider}
                  </Badge>
                ))}
              </div>
            </div>
          )}

        {/* Action buttons */}
        <div className="flex gap-2 pt-2">
          {cancelAtPeriodEnd && status === "active" ? (
            <Button className="flex-1" variant="default" onClick={onReactivate}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Reactivate Subscription
            </Button>
          ) : tier === "free" || isCanceled ? (
            <Button className="flex-1" onClick={onUpgrade}>
              <ArrowUpRight className="mr-2 h-4 w-4" />
              Upgrade Plan
            </Button>
          ) : tier !== "enterprise" && tier !== "lifetime" ? (
            <>
              <Button className="flex-1" variant="outline" onClick={onManage}>
                Manage Subscription
              </Button>
              <Button variant="outline" onClick={onUpgrade}>
                <ArrowUpRight className="mr-2 h-4 w-4" />
                Change Plan
              </Button>
            </>
          ) : tier === "lifetime" ? (
            <Button className="flex-1" variant="outline" onClick={onManage}>
              Manage Account
            </Button>
          ) : (
            <Button className="flex-1" variant="outline" onClick={onManage}>
              Contact Support
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function SubscriptionCardSkeleton({
  className,
}: {
  className?: string;
}) {
  return (
    <SubscriptionCard subscription={null} isLoading className={className} />
  );
}
