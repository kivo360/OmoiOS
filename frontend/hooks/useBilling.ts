/**
 * React Query hooks for Billing API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getStripeConfig,
  getBillingAccount,
  listPaymentMethods,
  attachPaymentMethod,
  removePaymentMethod,
  createCreditCheckout,
  createCustomerPortal,
  listInvoices,
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
  })
}

// ============================================================================
// Invoices
// ============================================================================

/**
 * Hook to list invoices
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
    },
  })
}

/**
 * Hook to create a lifetime checkout session
 */
export function useCreateLifetimeCheckout() {
  return useMutation<CheckoutResponse, Error, { orgId: string; request?: LifetimePurchaseRequest }>({
    mutationFn: ({ orgId, request }) => createLifetimeCheckout(orgId, request),
  })
}

/**
 * Hook to create a subscription checkout session (Pro or Team plans)
 */
export function useCreateSubscriptionCheckout() {
  return useMutation<CheckoutResponse, Error, { orgId: string; data: SubscriptionCheckoutRequest }>({
    mutationFn: ({ orgId, data }) => createSubscriptionCheckout(orgId, data),
  })
}
