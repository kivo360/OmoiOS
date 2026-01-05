/**
 * React Query hooks for Billing API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { track, ANALYTICS_EVENTS } from "@/lib/analytics"
import {
  getStripeConfig,
  getBillingAccount,
  listPaymentMethods,
  attachPaymentMethod,
  removePaymentMethod,
  createCreditCheckout,
  createCustomerPortal,
  listInvoices,
  listStripeInvoices,
  getInvoice,
  payInvoice,
  generateInvoice,
  getUsage,
  getSubscription,
  cancelSubscription,
  reactivateSubscription,
  createLifetimeCheckout,
  createSubscriptionCheckout,
  type SubscriptionCheckoutRequest,
} from "@/lib/api/billing"
import type {
  BillingAccount,
  Invoice,
  StripeInvoice,
  UsageRecord,
  PaymentMethod,
  StripeConfig,
  CheckoutResponse,
  PortalResponse,
  CreditPurchaseRequest,
  PaymentMethodRequest,
  Subscription,
  LifetimePurchaseRequest,
} from "@/lib/api/types"

// UUID validation regex - prevents API calls with invalid IDs
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isValidUUID(id: string | undefined): id is string {
  return !!id && UUID_REGEX.test(id)
}

// Query keys
export const billingKeys = {
  all: ["billing"] as const,
  config: () => [...billingKeys.all, "config"] as const,
  accounts: () => [...billingKeys.all, "accounts"] as const,
  account: (orgId: string) => [...billingKeys.accounts(), orgId] as const,
  subscription: (orgId: string) => [...billingKeys.account(orgId), "subscription"] as const,
  paymentMethods: (orgId: string) => [...billingKeys.account(orgId), "payment-methods"] as const,
  invoices: (orgId: string) => [...billingKeys.account(orgId), "invoices"] as const,
  stripeInvoices: (orgId: string) => [...billingKeys.account(orgId), "stripe-invoices"] as const,
  invoice: (invoiceId: string) => [...billingKeys.all, "invoice", invoiceId] as const,
  usage: (orgId: string) => [...billingKeys.account(orgId), "usage"] as const,
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Hook to get Stripe configuration
 */
export function useStripeConfig() {
  return useQuery<StripeConfig>({
    queryKey: billingKeys.config(),
    queryFn: getStripeConfig,
    staleTime: 1000 * 60 * 60, // 1 hour - config doesn't change often
  })
}

// ============================================================================
// Billing Account
// ============================================================================

/**
 * Hook to get or create billing account for an organization
 */
export function useBillingAccount(orgId: string | undefined) {
  return useQuery<BillingAccount>({
    queryKey: billingKeys.account(orgId!),
    queryFn: () => getBillingAccount(orgId!),
    enabled: isValidUUID(orgId),
  })
}

// ============================================================================
// Payment Methods
// ============================================================================

/**
 * Hook to list payment methods
 */
export function usePaymentMethods(orgId: string | undefined) {
  return useQuery<PaymentMethod[]>({
    queryKey: billingKeys.paymentMethods(orgId!),
    queryFn: () => listPaymentMethods(orgId!),
    enabled: isValidUUID(orgId),
  })
}

/**
 * Hook to attach a payment method
 */
export function useAttachPaymentMethod() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      orgId,
      data,
    }: {
      orgId: string
      data: PaymentMethodRequest
    }) => attachPaymentMethod(orgId, data),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.paymentMethods(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.account(orgId) })
    },
  })
}

/**
 * Hook to remove a payment method
 */
export function useRemovePaymentMethod() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      orgId,
      paymentMethodId,
    }: {
      orgId: string
      paymentMethodId: string
    }) => removePaymentMethod(orgId, paymentMethodId),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.paymentMethods(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.account(orgId) })
    },
  })
}

// ============================================================================
// Credit Purchase
// ============================================================================

/**
 * Hook to create a credit checkout session
 */
export function useCreateCreditCheckout() {
  return useMutation<CheckoutResponse, Error, { orgId: string; data: CreditPurchaseRequest }>({
    mutationFn: ({ orgId, data }) => createCreditCheckout(orgId, data),
    onSuccess: (response, { orgId, data }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_STARTED, {
        plan_type: 'free', // Credits are add-ons, not plan changes
        price_amount: data.amount_usd,
        currency: 'USD',
        organization_id: orgId,
      })
    },
    onError: (error, { orgId, data }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_FAILED, {
        plan_type: 'free',
        price_amount: data.amount_usd,
        organization_id: orgId,
        error_message: error.message,
      })
    },
  })
}

// ============================================================================
// Customer Portal
// ============================================================================

/**
 * Hook to create a customer portal session
 */
export function useCreateCustomerPortal() {
  return useMutation<PortalResponse, Error, string>({
    mutationFn: (orgId) => createCustomerPortal(orgId),
    onSuccess: (_, orgId) => {
      track(ANALYTICS_EVENTS.BILLING_PORTAL_OPENED, {
        page_path: window?.location?.pathname,
      })
    },
  })
}

// ============================================================================
// Invoices
// ============================================================================

/**
 * Hook to list invoices (from local database)
 */
export function useInvoices(
  orgId: string | undefined,
  options?: { status?: string; limit?: number }
) {
  return useQuery<Invoice[]>({
    queryKey: [...billingKeys.invoices(orgId!), options],
    queryFn: () => listInvoices(orgId!, options),
    enabled: isValidUUID(orgId),
  })
}

/**
 * Hook to list invoices directly from Stripe (includes subscription invoices)
 */
export function useStripeInvoices(
  orgId: string | undefined,
  options?: { status?: string; limit?: number }
) {
  return useQuery<StripeInvoice[]>({
    queryKey: [...billingKeys.stripeInvoices(orgId!), options],
    queryFn: () => listStripeInvoices(orgId!, options),
    enabled: isValidUUID(orgId),
  })
}

/**
 * Hook to get a specific invoice
 */
export function useInvoice(invoiceId: string | undefined) {
  return useQuery<Invoice>({
    queryKey: billingKeys.invoice(invoiceId!),
    queryFn: () => getInvoice(invoiceId!),
    enabled: isValidUUID(invoiceId),
  })
}

/**
 * Hook to pay an invoice
 */
export function usePayInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      invoiceId,
      paymentMethodId,
    }: {
      invoiceId: string
      paymentMethodId?: string
      orgId: string
    }) => payInvoice(invoiceId, paymentMethodId),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.invoices(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.account(orgId) })
    },
  })
}

/**
 * Hook to generate an invoice
 */
export function useGenerateInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (orgId: string) => generateInvoice(orgId),
    onSuccess: (_, orgId) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.invoices(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.usage(orgId) })
    },
  })
}

// ============================================================================
// Usage
// ============================================================================

/**
 * Hook to get usage records
 */
export function useUsage(
  orgId: string | undefined,
  options?: { billed?: boolean }
) {
  return useQuery<UsageRecord[]>({
    queryKey: [...billingKeys.usage(orgId!), options],
    queryFn: () => getUsage(orgId!, options),
    enabled: isValidUUID(orgId),
  })
}

/**
 * Usage summary type
 */
export interface UsageSummary {
  subscription_tier: string | null
  workflows_used: number
  workflows_limit: number
  free_workflows_remaining: number
  credit_balance: number
  can_execute: boolean
  reason: string
}

/**
 * Hook to get usage summary with limits and execution availability
 */
export function useUsageSummary(orgId: string | undefined) {
  return useQuery<UsageSummary>({
    queryKey: [...billingKeys.usage(orgId!), "summary"],
    queryFn: async () => {
      const { getUsageSummary } = await import("@/lib/api/billing")
      return getUsageSummary(orgId!)
    },
    enabled: isValidUUID(orgId),
    staleTime: 30 * 1000, // 30 seconds - usage can change frequently
  })
}

/**
 * Hook to check if an organization can execute a workflow
 */
export function useCanExecuteWorkflow(orgId: string | undefined) {
  return useQuery<{ can_execute: boolean; reason: string }>({
    queryKey: [...billingKeys.account(orgId!), "can-execute"],
    queryFn: async () => {
      const { checkWorkflowExecution } = await import("@/lib/api/billing")
      return checkWorkflowExecution(orgId!)
    },
    enabled: isValidUUID(orgId),
    staleTime: 30 * 1000, // 30 seconds
  })
}

// ============================================================================
// Subscription
// ============================================================================

/**
 * Hook to get the active subscription for an organization
 */
export function useSubscription(orgId: string | undefined) {
  return useQuery<Subscription | null>({
    queryKey: billingKeys.subscription(orgId!),
    queryFn: () => getSubscription(orgId!),
    enabled: isValidUUID(orgId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to cancel a subscription
 */
export function useCancelSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      orgId,
      atPeriodEnd = true,
    }: {
      orgId: string
      atPeriodEnd?: boolean
    }) => cancelSubscription(orgId, atPeriodEnd),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.subscription(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.account(orgId) })
      track(ANALYTICS_EVENTS.SUBSCRIPTION_CANCELLED, {
        organization_id: orgId,
        plan_type: 'pro', // Could be enhanced to get actual tier
      })
    },
  })
}

/**
 * Hook to reactivate a canceled subscription
 */
export function useReactivateSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (orgId: string) => reactivateSubscription(orgId),
    onSuccess: (_, orgId) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.subscription(orgId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.account(orgId) })
      track(ANALYTICS_EVENTS.SUBSCRIPTION_REACTIVATED, {
        organization_id: orgId,
        plan_type: 'pro', // Could be enhanced to get actual tier
      })
    },
  })
}

/**
 * Hook to create a lifetime checkout session
 */
export function useCreateLifetimeCheckout() {
  return useMutation<CheckoutResponse, Error, { orgId: string; request?: LifetimePurchaseRequest }>({
    mutationFn: ({ orgId, request }) => createLifetimeCheckout(orgId, request),
    onSuccess: (response, { orgId }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_STARTED, {
        plan_type: 'lifetime',
        price_amount: 299, // Lifetime plan price
        currency: 'USD',
        organization_id: orgId,
      })
    },
    onError: (error, { orgId }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_FAILED, {
        plan_type: 'lifetime',
        organization_id: orgId,
        error_message: error.message,
      })
    },
  })
}

/**
 * Hook to create a subscription checkout session (Pro or Team plans)
 */
export function useCreateSubscriptionCheckout() {
  return useMutation<CheckoutResponse, Error, { orgId: string; data: SubscriptionCheckoutRequest }>({
    mutationFn: ({ orgId, data }) => createSubscriptionCheckout(orgId, data),
    onSuccess: (response, { orgId, data }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_STARTED, {
        plan_type: data.tier,
        price_amount: data.tier === 'pro' ? 50 : 150, // Pro = $50, Team = $150
        currency: 'USD',
        organization_id: orgId,
      })
    },
    onError: (error, { orgId, data }) => {
      track(ANALYTICS_EVENTS.CHECKOUT_FAILED, {
        plan_type: data.tier,
        organization_id: orgId,
        error_message: error.message,
      })
    },
  })
}
