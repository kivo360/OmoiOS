/**
 * Billing API client for payment processing and account management
 */

import { api } from "./client"
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
  Payment,
  Subscription,
  LifetimePurchaseRequest,
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
