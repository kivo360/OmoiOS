"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  CreditCard,
  DollarSign,
  Zap,
  Receipt,
  AlertCircle,
  Plus,
  Trash2,
  Settings,
  Loader2,
  Crown,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useOrganization } from "@/hooks/useOrganizations";
import {
  useBillingAccount,
  usePaymentMethods,
  useStripeInvoices,
  useUsage,
  useCreateCreditCheckout,
  useCreateCustomerPortal,
  useRemovePaymentMethod,
  useStripeConfig,
  useSubscription,
  useCancelSubscription,
  useReactivateSubscription,
  useCreateLifetimeCheckout,
  useCreateSubscriptionCheckout,
} from "@/hooks/useBilling";
import { SubscriptionCard } from "@/components/billing/SubscriptionCard";
import { UpgradeDialog } from "@/components/billing/UpgradeDialog";
import type { SubscriptionTier } from "@/lib/api/types";

interface BillingPageProps {
  params: Promise<{ id: string }>;
}

export default function BillingPage({ params }: BillingPageProps) {
  const { id: orgId } = use(params);
  const { toast } = useToast();
  const [creditAmount, setCreditAmount] = useState("50");
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
  const [upgradeError, setUpgradeError] = useState<string | null>(null);

  // Fetch data
  const {
    data: org,
    isLoading: orgLoading,
    error: orgError,
  } = useOrganization(orgId);
  const { data: account, isLoading: accountLoading } = useBillingAccount(orgId);
  const { data: subscription, isLoading: subscriptionLoading } =
    useSubscription(orgId);
  const { data: paymentMethods, isLoading: pmLoading } =
    usePaymentMethods(orgId);
  const { data: stripeInvoices, isLoading: invoicesLoading } =
    useStripeInvoices(orgId, { limit: 10 });
  const { data: usage, isLoading: usageLoading } = useUsage(orgId, {
    billed: false,
  });
  const { data: stripeConfig } = useStripeConfig();

  // Mutations
  const createCheckout = useCreateCreditCheckout();
  const createPortal = useCreateCustomerPortal();
  const removePaymentMethod = useRemovePaymentMethod();
  const cancelSubscription = useCancelSubscription();
  const reactivateSubscription = useReactivateSubscription();
  const createLifetimeCheckout = useCreateLifetimeCheckout();
  const createSubscriptionCheckout = useCreateSubscriptionCheckout();

  const handleBuyCredits = async () => {
    const amount = parseFloat(creditAmount);
    if (isNaN(amount) || amount < 10 || amount > 1000) {
      toast({
        title: "Invalid amount",
        description: "Please enter an amount between $10 and $1000",
        variant: "destructive",
      });
      return;
    }

    try {
      const result = await createCheckout.mutateAsync({
        orgId,
        data: { amount_usd: amount },
      });
      // Redirect to Stripe checkout
      window.location.href = result.checkout_url;
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create checkout session. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleOpenPortal = async () => {
    try {
      const result = await createPortal.mutateAsync(orgId);
      window.open(result.portal_url, "_blank");
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to open billing portal. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleRemovePaymentMethod = async (paymentMethodId: string) => {
    try {
      await removePaymentMethod.mutateAsync({ orgId, paymentMethodId });
      toast({
        title: "Payment method removed",
        description: "The payment method has been removed from your account.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to remove payment method. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpgrade = () => {
    setUpgradeError(null);
    setUpgradeDialogOpen(true);
  };

  const handleSelectTier = async (tier: SubscriptionTier) => {
    setUpgradeError(null);
    try {
      if (tier === "enterprise") {
        // Open enterprise contact form or email
        window.open(
          "mailto:sales@omoios.com?subject=Enterprise%20Plan%20Inquiry",
          "_blank",
        );
        setUpgradeDialogOpen(false);
        return;
      }

      if (tier === "lifetime") {
        const result = await createLifetimeCheckout.mutateAsync({ orgId });
        window.location.href = result.checkout_url;
        return;
      }

      // For pro and team tiers, create a subscription checkout session
      if (tier === "pro" || tier === "team") {
        const result = await createSubscriptionCheckout.mutateAsync({
          orgId,
          data: {
            tier,
            success_url: `${window.location.origin}/organizations/${orgId}/billing?checkout=success`,
            cancel_url: `${window.location.origin}/organizations/${orgId}/billing?checkout=cancelled`,
          },
        });
        window.location.href = result.checkout_url;
        return;
      }

      // Fallback: open the portal for other tiers
      const result = await createPortal.mutateAsync(orgId);
      window.open(result.portal_url, "_blank");
      setUpgradeDialogOpen(false);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to process upgrade. Please try again.";

      // If user already has a paid subscription, redirect to customer portal for plan changes
      if (
        errorMessage
          .toLowerCase()
          .includes("already has an active paid subscription") ||
        errorMessage.toLowerCase().includes("use the customer portal")
      ) {
        try {
          const result = await createPortal.mutateAsync(orgId);
          window.open(result.portal_url, "_blank");
          setUpgradeDialogOpen(false);
          toast({
            title: "Opening Billing Portal",
            description:
              "Use the Stripe portal to manage your subscription and change plans.",
          });
          return;
        } catch (portalError) {
          setUpgradeError(
            "Failed to open billing portal. Please try the 'Billing Portal' button.",
          );
          return;
        }
      }

      setUpgradeError(errorMessage);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      await cancelSubscription.mutateAsync({ orgId, atPeriodEnd: true });
      toast({
        title: "Subscription canceled",
        description:
          "Your subscription will end at the end of the current billing period.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to cancel subscription. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      await reactivateSubscription.mutateAsync(orgId);
      toast({
        title: "Subscription reactivated",
        description: "Your subscription has been reactivated.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to reactivate subscription. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Loading state
  if (orgLoading || accountLoading) {
    return (
      <div className="container mx-auto max-w-5xl p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (orgError) {
    return (
      <div className="container mx-auto max-w-5xl p-6 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
        <h1 className="mt-4 text-2xl font-bold">Failed to load billing</h1>
        <p className="mt-2 text-muted-foreground">
          {orgError instanceof Error ? orgError.message : "An error occurred"}
        </p>
        <Button className="mt-4" asChild>
          <Link href={`/organizations/${orgId}`}>Back to Organization</Link>
        </Button>
      </div>
    );
  }

  if (!org || !account) {
    return (
      <div className="container mx-auto max-w-5xl p-6 text-center">
        <h1 className="text-2xl font-bold">Organization not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/organizations">Back to Organizations</Link>
        </Button>
      </div>
    );
  }

  const statusColors: Record<
    string,
    "default" | "secondary" | "destructive" | "outline"
  > = {
    active: "default",
    pending: "secondary",
    suspended: "destructive",
  };

  return (
    <div className="container mx-auto max-w-5xl p-6 space-y-6">
      <Link
        href={`/organizations/${orgId}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to {org.name}
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Billing</h1>
          <p className="text-muted-foreground">
            Manage billing, credits, and payment methods for {org.name}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleOpenPortal}
          disabled={createPortal.isPending}
        >
          {createPortal.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Settings className="mr-2 h-4 w-4" />
          )}
          Billing Portal
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <DollarSign className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  ${account.credit_balance.toFixed(2)}
                </p>
                <p className="text-sm text-muted-foreground">Credit Balance</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                <Zap className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                {/* Show subscription workflows if subscribed, otherwise free tier */}
                {subscription && subscription.tier !== "free" ? (
                  <>
                    <p className="text-2xl font-bold">
                      {subscription.workflows_remaining === -1
                        ? "∞"
                        : subscription.workflows_remaining}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Workflows Left
                      {subscription.workflows_limit !== -1 &&
                        ` / ${subscription.workflows_limit}`}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-2xl font-bold">
                      {account.free_workflows_remaining}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Free Workflows Left
                    </p>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10">
                <Receipt className="h-5 w-5 text-purple-500" />
              </div>
              <div>
                {/* Show subscription usage if subscribed, otherwise total */}
                {subscription && subscription.tier !== "free" ? (
                  <>
                    <p className="text-2xl font-bold">
                      {subscription.workflows_used}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Workflows Used This Period
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-2xl font-bold">
                      {account.total_workflows_completed}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Workflows Completed
                    </p>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                <CreditCard className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  ${account.total_amount_spent.toFixed(2)}
                </p>
                <p className="text-sm text-muted-foreground">Total Spent</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Account Status</CardTitle>
              <CardDescription>
                Your billing account information
              </CardDescription>
            </div>
            <Badge variant={statusColors[account.status] || "secondary"}>
              {account.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Billing Email
              </p>
              <p className="text-sm">
                {account.billing_email || org.billing_email || "Not set"}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Free Tier Reset
              </p>
              <p className="text-sm">
                {account.free_workflows_reset_at
                  ? new Date(
                      account.free_workflows_reset_at,
                    ).toLocaleDateString()
                  : "N/A"}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Auto-Billing
              </p>
              <p className="text-sm">
                {account.auto_billing_enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Tax Exempt
              </p>
              <p className="text-sm">{account.tax_exempt ? "Yes" : "No"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="subscription" className="space-y-4">
        <TabsList>
          <TabsTrigger value="subscription">
            <Crown className="mr-2 h-4 w-4" />
            Subscription
          </TabsTrigger>
          <TabsTrigger value="credits">Credits</TabsTrigger>
          <TabsTrigger value="payment-methods">Payment Methods</TabsTrigger>
          <TabsTrigger value="invoices">Invoices</TabsTrigger>
          <TabsTrigger value="usage">Usage</TabsTrigger>
        </TabsList>

        {/* Subscription Tab */}
        <TabsContent value="subscription" className="space-y-4">
          <SubscriptionCard
            subscription={subscription}
            isLoading={subscriptionLoading}
            onUpgrade={handleUpgrade}
            onManage={handleOpenPortal}
            onCancel={handleCancelSubscription}
            onReactivate={handleReactivateSubscription}
          />
        </TabsContent>

        {/* Credits Tab */}
        <TabsContent value="credits" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Buy Credits</CardTitle>
              <CardDescription>
                Purchase prepaid credits to use for workflow completions. Each
                workflow costs $10.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-end gap-4">
                <div className="flex-1 max-w-xs">
                  <Label htmlFor="credit-amount">Amount (USD)</Label>
                  <Input
                    id="credit-amount"
                    type="number"
                    min="10"
                    max="1000"
                    value={creditAmount}
                    onChange={(e) => setCreditAmount(e.target.value)}
                    placeholder="50"
                  />
                </div>
                <Button
                  onClick={handleBuyCredits}
                  disabled={
                    createCheckout.isPending || !stripeConfig?.is_configured
                  }
                >
                  {createCheckout.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="mr-2 h-4 w-4" />
                  )}
                  Buy Credits
                </Button>
              </div>
              {!stripeConfig?.is_configured && (
                <p className="text-sm text-muted-foreground">
                  Stripe is not configured. Contact your administrator.
                </p>
              )}
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Quick options:</p>
                <div className="flex gap-2">
                  {[25, 50, 100, 250, 500].map((amount) => (
                    <Button
                      key={amount}
                      variant="outline"
                      size="sm"
                      onClick={() => setCreditAmount(amount.toString())}
                    >
                      ${amount}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payment Methods Tab */}
        <TabsContent value="payment-methods" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Payment Methods</CardTitle>
                  <CardDescription>
                    Manage your saved payment methods
                  </CardDescription>
                </div>
                <Button variant="outline" onClick={handleOpenPortal}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Payment Method
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {pmLoading ? (
                <div className="space-y-2">
                  {[1, 2].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : paymentMethods && paymentMethods.length > 0 ? (
                <div className="space-y-2">
                  {paymentMethods.map((pm) => (
                    <div
                      key={pm.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <CreditCard className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium">
                            {pm.card_brand
                              ? pm.card_brand.charAt(0).toUpperCase() +
                                pm.card_brand.slice(1)
                              : pm.type}{" "}
                            ending in {pm.card_last4 || "****"}
                          </p>
                          {pm.is_default && (
                            <Badge variant="secondary" className="mt-1">
                              Default
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemovePaymentMethod(pm.id)}
                        disabled={removePaymentMethod.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <CreditCard className="mx-auto h-12 w-12 text-muted-foreground" />
                  <p className="mt-2 text-muted-foreground">
                    No payment methods added
                  </p>
                  <Button
                    className="mt-4"
                    variant="outline"
                    onClick={handleOpenPortal}
                  >
                    Add Payment Method
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Invoices Tab */}
        <TabsContent value="invoices" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Invoices</CardTitle>
              <CardDescription>Your billing history</CardDescription>
            </CardHeader>
            <CardContent>
              {invoicesLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : stripeInvoices && stripeInvoices.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invoice #</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stripeInvoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        <TableCell className="font-mono">
                          {invoice.number || invoice.id}
                        </TableCell>
                        <TableCell>
                          {invoice.created
                            ? new Date(invoice.created).toLocaleDateString()
                            : "N/A"}
                        </TableCell>
                        <TableCell>
                          ${(invoice.total / 100).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              invoice.status === "paid"
                                ? "default"
                                : invoice.status === "open"
                                  ? "secondary"
                                  : "destructive"
                            }
                          >
                            {invoice.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {invoice.hosted_invoice_url ? (
                            <Button variant="ghost" size="sm" asChild>
                              <a
                                href={invoice.hosted_invoice_url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                View
                              </a>
                            </Button>
                          ) : invoice.invoice_pdf ? (
                            <Button variant="ghost" size="sm" asChild>
                              <a
                                href={invoice.invoice_pdf}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                PDF
                              </a>
                            </Button>
                          ) : null}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">
                  <Receipt className="mx-auto h-12 w-12 text-muted-foreground" />
                  <p className="mt-2 text-muted-foreground">No invoices yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Usage Tab */}
        <TabsContent value="usage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Usage</CardTitle>
              <CardDescription>
                Unbilled usage for the current period
              </CardDescription>
            </CardHeader>
            <CardContent>
              {usageLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : usage && usage.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Free Tier</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usage.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          {record.recorded_at
                            ? new Date(record.recorded_at).toLocaleDateString()
                            : "N/A"}
                        </TableCell>
                        <TableCell>{record.usage_type}</TableCell>
                        <TableCell>{record.quantity}</TableCell>
                        <TableCell>${record.total_price.toFixed(2)}</TableCell>
                        <TableCell>
                          {record.free_tier_used ? (
                            <Badge variant="outline">Free</Badge>
                          ) : (
                            <Badge variant="secondary">Paid</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">
                  <Zap className="mx-auto h-12 w-12 text-muted-foreground" />
                  <p className="mt-2 text-muted-foreground">
                    No usage recorded this period
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Upgrade Dialog */}
      <UpgradeDialog
        open={upgradeDialogOpen}
        onOpenChange={setUpgradeDialogOpen}
        currentTier={subscription?.tier || "free"}
        onSelectTier={handleSelectTier}
        isLoading={
          createLifetimeCheckout.isPending ||
          createPortal.isPending ||
          createSubscriptionCheckout.isPending
        }
        error={upgradeError}
      />
    </div>
  );
}
