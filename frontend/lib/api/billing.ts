/**
 * Billing API client for payment processing and account management
 */

import { api } from "./client"
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
  Payment,
  Subscription,
  LifetimePurchaseRequest,
  PromoCodeValidateRequest,
  PromoCodeValidateResponse,
  PromoCodeRedeemRequest,
  PromoCodeRedeemResponse,
} from "./types"

// ============================================================================
// Stripe Configuration
// ============================================================================

/**
 * Get Stripe configuration (publishable key) for frontend
 */
export async function getStripeConfig(): Promise<StripeConfig> {
  return api.get<StripeConfig>("/api/v1/billing/config")
}

// ============================================================================
// Billing Account
// ============================================================================

/**
 * Get or create billing account for an organization
 */
export async function getBillingAccount(organizationId: string): Promise<BillingAccount> {
  return api.get<BillingAccount>(`/api/v1/billing/account/${organizationId}`)
}

// ============================================================================
// Payment Methods
// ============================================================================

/**
 * Attach a payment method to the billing account
 */
export async function attachPaymentMethod(
  organizationId: string,
  request: PaymentMethodRequest
): Promise<PaymentMethod> {
  return api.post<PaymentMethod>(
    `/api/v1/billing/account/${organizationId}/payment-method`,
    request
  )
}

/**
 * List all payment methods for the billing account
 */
export async function listPaymentMethods(organizationId: string): Promise<PaymentMethod[]> {
  return api.get<PaymentMethod[]>(`/api/v1/billing/account/${organizationId}/payment-methods`)
}

/**
 * Remove a payment method from the billing account
 */
export async function removePaymentMethod(
  organizationId: string,
  paymentMethodId: string
): Promise<{ status: string; message: string }> {
  return api.delete<{ status: string; message: string }>(
    `/api/v1/billing/account/${organizationId}/payment-methods/${paymentMethodId}`
  )
}

// ============================================================================
// Credit Purchase
// ============================================================================

/**
 * Create a checkout session to purchase prepaid credits
 */
export async function createCreditCheckout(
  organizationId: string,
  request: CreditPurchaseRequest
): Promise<CheckoutResponse> {
  return api.post<CheckoutResponse>(
    `/api/v1/billing/account/${organizationId}/credits/checkout`,
    request
  )
}

// ============================================================================
// Customer Portal
// ============================================================================

/**
 * Create a Stripe Customer Portal session
 */
export async function createCustomerPortal(organizationId: string): Promise<PortalResponse> {
  return api.post<PortalResponse>(`/api/v1/billing/account/${organizationId}/portal`)
}

// ============================================================================
// Invoices
// ============================================================================

/**
 * List invoices for an organization
 */
export async function listInvoices(
  organizationId: string,
  options?: { status?: string; limit?: number }
): Promise<Invoice[]> {
  let endpoint = `/api/v1/billing/account/${organizationId}/invoices`
  const params = new URLSearchParams()
  if (options?.status) params.append("status", options.status)
  if (options?.limit) params.append("limit", options.limit.toString())
  if (params.toString()) endpoint += `?${params.toString()}`
  return api.get<Invoice[]>(endpoint)
}

/**
 * Get a specific invoice by ID
 */
export async function getInvoice(invoiceId: string): Promise<Invoice> {
  return api.get<Invoice>(`/api/v1/billing/invoices/${invoiceId}`)
}

/**
 * Pay an invoice
 */
export async function payInvoice(
  invoiceId: string,
  paymentMethodId?: string
): Promise<Payment> {
  return api.post<Payment>(
    `/api/v1/billing/invoices/${invoiceId}/pay`,
    paymentMethodId ? { payment_method_id: paymentMethodId } : undefined
  )
}

/**
 * Generate an invoice for unbilled usage
 */
export async function generateInvoice(organizationId: string): Promise<Invoice | null> {
  return api.post<Invoice | null>(`/api/v1/billing/account/${organizationId}/invoices/generate`)
}

/**
 * List invoices directly from Stripe (includes subscription invoices)
 */
export async function listStripeInvoices(
  organizationId: string,
  options?: { status?: string; limit?: number }
): Promise<StripeInvoice[]> {
  let endpoint = `/api/v1/billing/account/${organizationId}/stripe-invoices`
  const params = new URLSearchParams()
  if (options?.status) params.append("status", options.status)
  if (options?.limit) params.append("limit", options.limit.toString())
  if (params.toString()) endpoint += `?${params.toString()}`
  return api.get<StripeInvoice[]>(endpoint)
}

// ============================================================================
// Usage Records
// ============================================================================

/**
 * Get usage records for an organization
 */
export async function getUsage(
  organizationId: string,
  options?: { billed?: boolean }
): Promise<UsageRecord[]> {
  let endpoint = `/api/v1/billing/account/${organizationId}/usage`
  if (options?.billed !== undefined) {
    endpoint += `?billed=${options.billed}`
  }
  return api.get<UsageRecord[]>(endpoint)
}

/**
 * Usage summary for workflow execution limits
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
 * Get usage summary for an organization
 * Includes subscription tier, workflow limits, and execution availability
 */
export async function getUsageSummary(organizationId: string): Promise<UsageSummary> {
  return api.get<UsageSummary>(`/api/v1/billing/account/${organizationId}/usage-summary`)
}

/**
 * Check if an organization can execute a workflow
 * Returns whether execution is allowed and the reason
 */
export async function checkWorkflowExecution(
  organizationId: string
): Promise<{ can_execute: boolean; reason: string }> {
  return api.post<{ can_execute: boolean; reason: string }>(
    `/api/v1/billing/account/${organizationId}/check-execution`
  )
}

// ============================================================================
// Subscription Management
// ============================================================================

/**
 * Get the active subscription for an organization
 */
export async function getSubscription(organizationId: string): Promise<Subscription | null> {
  return api.get<Subscription | null>(`/api/v1/billing/account/${organizationId}/subscription`)
}

/**
 * Cancel the subscription for an organization
 * @param atPeriodEnd - If true, cancel at end of billing period. If false, cancel immediately.
 */
export async function cancelSubscription(
  organizationId: string,
  atPeriodEnd: boolean = true
): Promise<{ status: string; message: string }> {
  return api.post<{ status: string; message: string }>(
    `/api/v1/billing/account/${organizationId}/subscription/cancel?at_period_end=${atPeriodEnd}`
  )
}

/**
 * Reactivate a canceled subscription
 */
export async function reactivateSubscription(
  organizationId: string
): Promise<{ status: string; message: string }> {
  return api.post<{ status: string; message: string }>(
    `/api/v1/billing/account/${organizationId}/subscription/reactivate`
  )
}

/**
 * Create a checkout session for lifetime purchase
 */
export async function createLifetimeCheckout(
  organizationId: string,
  request?: LifetimePurchaseRequest
): Promise<CheckoutResponse> {
  return api.post<CheckoutResponse>(
    `/api/v1/billing/account/${organizationId}/lifetime/checkout`,
    request
  )
}

/**
 * Create a checkout session for subscription (Pro or Team)
 */
export interface SubscriptionCheckoutRequest {
  tier: "pro" | "team"
  success_url?: string
  cancel_url?: string
}

export async function createSubscriptionCheckout(
  organizationId: string,
  request: SubscriptionCheckoutRequest
): Promise<CheckoutResponse> {
  return api.post<CheckoutResponse>(
    `/api/v1/billing/account/${organizationId}/subscription/checkout`,
    request
  )
}

// ============================================================================
// Promo Codes
// ============================================================================

/**
 * Validate a promo code without redeeming it
 */
export async function validatePromoCode(
  request: PromoCodeValidateRequest
): Promise<PromoCodeValidateResponse> {
  return api.post<PromoCodeValidateResponse>("/api/v1/billing/promo-codes/validate", request)
}

/**
 * Redeem a promo code for an organization
 * This will apply the promo code benefits (discount, free tier, etc.)
 */
export async function redeemPromoCode(
  organizationId: string,
  request: PromoCodeRedeemRequest
): Promise<PromoCodeRedeemResponse> {
  return api.post<PromoCodeRedeemResponse>(
    `/api/v1/billing/account/${organizationId}/promo-codes/redeem`,
    request
  )
}
