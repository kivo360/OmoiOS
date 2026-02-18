/**
 * Analytics Event Definitions
 *
 * Centralized type-safe event definitions for PostHog analytics.
 * All events should be defined here with their expected properties.
 */

// ============================================================================
// Event Names
// ============================================================================

/**
 * All analytics event names as const for type safety
 */
export const ANALYTICS_EVENTS = {
  // Onboarding events
  ONBOARDING_STEP_VIEWED: "onboarding_step_viewed",
  ONBOARDING_STEP_COMPLETED: "onboarding_step_completed",
  ONBOARDING_STEP_SKIPPED: "onboarding_step_skipped",
  ONBOARDING_COMPLETED: "onboarding_completed",
  ONBOARDING_FULLY_COMPLETED: "onboarding_fully_completed",
  CHECKLIST_ITEM_COMPLETED: "checklist_item_completed",
  FIRST_SPEC_SUBMITTED: "first_spec_submitted",

  // Authentication events
  USER_SIGNED_UP: "user_signed_up",
  USER_LOGGED_IN: "user_logged_in",
  USER_LOGGED_OUT: "user_logged_out",
  PASSWORD_RESET_REQUESTED: "password_reset_requested",
  PASSWORD_RESET_COMPLETED: "password_reset_completed",
  EMAIL_VERIFIED: "email_verified",

  // GitHub integration events
  GITHUB_CONNECTED: "github_connected",
  GITHUB_DISCONNECTED: "github_disconnected",
  GITHUB_REPO_SELECTED: "github_repo_selected",

  // Project events
  PROJECT_CREATED: "project_created",
  PROJECT_UPDATED: "project_updated",
  PROJECT_DELETED: "project_deleted",
  PROJECT_VIEWED: "project_viewed",

  // Spec/Sandbox events
  SPEC_CREATED: "spec_created",
  SPEC_SUBMITTED: "spec_submitted",
  SPEC_COMPLETED: "spec_completed",
  SPEC_FAILED: "spec_failed",
  SANDBOX_STARTED: "sandbox_started",
  SANDBOX_COMPLETED: "sandbox_completed",
  SANDBOX_VIEWED: "sandbox_viewed",

  // Billing/Checkout events
  CHECKOUT_STARTED: "checkout_started",
  CHECKOUT_COMPLETED: "checkout_completed",
  CHECKOUT_FAILED: "checkout_failed",
  CHECKOUT_CANCELLED: "checkout_cancelled",
  SUBSCRIPTION_CREATED: "subscription_created",
  SUBSCRIPTION_CANCELLED: "subscription_cancelled",
  SUBSCRIPTION_REACTIVATED: "subscription_reactivated",
  LIFETIME_PURCHASED: "lifetime_purchased",
  CREDITS_PURCHASED: "credits_purchased",
  PLAN_UPGRADED: "plan_upgraded",
  PLAN_DOWNGRADED: "plan_downgraded",
  BILLING_PORTAL_OPENED: "billing_portal_opened",
  PROMO_CODE_REDEEMED: "promo_code_redeemed",
  PROMO_CODE_FAILED: "promo_code_failed",

  // Feature usage events
  FEATURE_USED: "feature_used",
  COMMAND_EXECUTED: "command_executed",
  BOARD_VIEWED: "board_viewed",
  TICKET_CREATED: "ticket_created",
  TICKET_MOVED: "ticket_moved",
  AGENT_SPAWNED: "agent_spawned",

  // Navigation events
  PAGE_VIEWED: "page_viewed",
  TAB_CLICKED: "tab_clicked",
  MODAL_OPENED: "modal_opened",
  MODAL_CLOSED: "modal_closed",

  // Error events
  ERROR_OCCURRED: "error_occurred",
  API_ERROR: "api_error",
  VALIDATION_ERROR: "validation_error",

  // Organization events
  ORGANIZATION_CREATED: "organization_created",
  ORGANIZATION_UPDATED: "organization_updated",
  TEAM_MEMBER_INVITED: "team_member_invited",
  TEAM_MEMBER_REMOVED: "team_member_removed",
} as const;

export type AnalyticsEventName =
  (typeof ANALYTICS_EVENTS)[keyof typeof ANALYTICS_EVENTS];

// ============================================================================
// Event Property Types
// ============================================================================

/**
 * Base properties included with every event
 */
export interface BaseEventProperties {
  // Page context
  page_path?: string;
  page_title?: string;
  page_referrer?: string;

  // Session context
  session_id?: string;

  // Timestamp (usually handled by PostHog)
  timestamp?: string;
}

/**
 * Onboarding step event properties
 */
export interface OnboardingStepProperties extends BaseEventProperties {
  step: "welcome" | "github" | "repo" | "first-spec" | "plan" | "complete";
  step_number?: number;
  time_on_step_seconds?: number;
}

/**
 * Onboarding completion event properties
 */
export interface OnboardingCompletedProperties extends BaseEventProperties {
  selected_plan?: string;
  has_first_spec?: boolean;
  github_connected?: boolean;
  total_time_seconds?: number;
  completed_items?: string[];
}

/**
 * Checklist item event properties
 */
export interface ChecklistItemProperties extends BaseEventProperties {
  item_id: string;
  item_name?: string;
}

/**
 * First spec submission event properties
 */
export interface FirstSpecProperties extends BaseEventProperties {
  spec_length: number;
  project_id?: string;
  has_github?: boolean;
}

/**
 * Checkout event properties
 */
export interface CheckoutProperties extends BaseEventProperties {
  plan_type: "free" | "pro" | "team" | "enterprise" | "lifetime";
  price_amount?: number;
  currency?: string;
  organization_id?: string;
  is_upgrade?: boolean;
  from_plan?: string;
}

/**
 * Checkout completed properties (includes payment details)
 */
export interface CheckoutCompletedProperties extends CheckoutProperties {
  payment_method_type?: string;
  stripe_session_id?: string;
}

/**
 * Checkout failed properties (includes error details)
 */
export interface CheckoutFailedProperties extends CheckoutProperties {
  error_code?: string;
  error_message?: string;
}

/**
 * GitHub connection event properties
 */
export interface GitHubConnectionProperties extends BaseEventProperties {
  username?: string;
  connected_repos_count?: number;
}

/**
 * GitHub repo selection event properties
 */
export interface GitHubRepoSelectedProperties extends BaseEventProperties {
  repo_owner: string;
  repo_name: string;
  repo_full_name: string;
  repo_language?: string;
  is_private?: boolean;
}

/**
 * Project event properties
 */
export interface ProjectEventProperties extends BaseEventProperties {
  project_id: string;
  project_name?: string;
  github_connected?: boolean;
  organization_id?: string;
}

/**
 * Spec/Sandbox event properties
 */
export interface SpecEventProperties extends BaseEventProperties {
  spec_id?: string;
  sandbox_id?: string;
  project_id?: string;
  spec_length?: number;
  model?: string;
  status?: string;
  duration_seconds?: number;
}

/**
 * Feature usage event properties
 */
export interface FeatureUsageProperties extends BaseEventProperties {
  feature_name: string;
  feature_category?: string;
  action?: string;
  success?: boolean;
}

/**
 * Error event properties
 */
export interface ErrorEventProperties extends BaseEventProperties {
  error_type: string;
  error_message?: string;
  error_code?: string;
  error_stack?: string;
  api_endpoint?: string;
  http_status?: number;
}

/**
 * Authentication event properties
 */
export interface AuthEventProperties extends BaseEventProperties {
  auth_method?: "email" | "github" | "google";
  referral_source?: string;
}

/**
 * Navigation event properties
 */
export interface NavigationEventProperties extends BaseEventProperties {
  from_path?: string;
  to_path?: string;
  navigation_type?: "link" | "button" | "programmatic";
}

/**
 * Organization event properties
 */
export interface OrganizationEventProperties extends BaseEventProperties {
  organization_id: string;
  organization_name?: string;
  member_count?: number;
  action?: string;
}

/**
 * Promo code event properties
 */
export interface PromoCodeEventProperties extends BaseEventProperties {
  organization_id?: string;
  code?: string;
  discount_type?: string;
  tier_granted?: string | null;
  error_message?: string;
}

// ============================================================================
// Event Properties Union Type
// ============================================================================

/**
 * Map of event names to their property types
 */
export interface EventPropertiesMap {
  [ANALYTICS_EVENTS.ONBOARDING_STEP_VIEWED]: OnboardingStepProperties;
  [ANALYTICS_EVENTS.ONBOARDING_STEP_COMPLETED]: OnboardingStepProperties;
  [ANALYTICS_EVENTS.ONBOARDING_STEP_SKIPPED]: OnboardingStepProperties;
  [ANALYTICS_EVENTS.ONBOARDING_COMPLETED]: OnboardingCompletedProperties;
  [ANALYTICS_EVENTS.ONBOARDING_FULLY_COMPLETED]: OnboardingCompletedProperties;
  [ANALYTICS_EVENTS.CHECKLIST_ITEM_COMPLETED]: ChecklistItemProperties;
  [ANALYTICS_EVENTS.FIRST_SPEC_SUBMITTED]: FirstSpecProperties;
  [ANALYTICS_EVENTS.USER_SIGNED_UP]: AuthEventProperties;
  [ANALYTICS_EVENTS.USER_LOGGED_IN]: AuthEventProperties;
  [ANALYTICS_EVENTS.USER_LOGGED_OUT]: AuthEventProperties;
  [ANALYTICS_EVENTS.GITHUB_CONNECTED]: GitHubConnectionProperties;
  [ANALYTICS_EVENTS.GITHUB_DISCONNECTED]: GitHubConnectionProperties;
  [ANALYTICS_EVENTS.GITHUB_REPO_SELECTED]: GitHubRepoSelectedProperties;
  [ANALYTICS_EVENTS.PROJECT_CREATED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.PROJECT_UPDATED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.PROJECT_DELETED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.PROJECT_VIEWED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.SPEC_CREATED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SPEC_SUBMITTED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SPEC_COMPLETED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SPEC_FAILED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SANDBOX_STARTED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SANDBOX_COMPLETED]: SpecEventProperties;
  [ANALYTICS_EVENTS.SANDBOX_VIEWED]: SpecEventProperties;
  [ANALYTICS_EVENTS.CHECKOUT_STARTED]: CheckoutProperties;
  [ANALYTICS_EVENTS.CHECKOUT_COMPLETED]: CheckoutCompletedProperties;
  [ANALYTICS_EVENTS.CHECKOUT_FAILED]: CheckoutFailedProperties;
  [ANALYTICS_EVENTS.CHECKOUT_CANCELLED]: CheckoutProperties;
  [ANALYTICS_EVENTS.SUBSCRIPTION_CREATED]: CheckoutProperties;
  [ANALYTICS_EVENTS.SUBSCRIPTION_CANCELLED]: CheckoutProperties;
  [ANALYTICS_EVENTS.SUBSCRIPTION_REACTIVATED]: CheckoutProperties;
  [ANALYTICS_EVENTS.LIFETIME_PURCHASED]: CheckoutCompletedProperties;
  [ANALYTICS_EVENTS.CREDITS_PURCHASED]: CheckoutCompletedProperties;
  [ANALYTICS_EVENTS.PLAN_UPGRADED]: CheckoutProperties;
  [ANALYTICS_EVENTS.PLAN_DOWNGRADED]: CheckoutProperties;
  [ANALYTICS_EVENTS.BILLING_PORTAL_OPENED]: BaseEventProperties;
  [ANALYTICS_EVENTS.FEATURE_USED]: FeatureUsageProperties;
  [ANALYTICS_EVENTS.COMMAND_EXECUTED]: FeatureUsageProperties;
  [ANALYTICS_EVENTS.BOARD_VIEWED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.TICKET_CREATED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.TICKET_MOVED]: ProjectEventProperties;
  [ANALYTICS_EVENTS.AGENT_SPAWNED]: SpecEventProperties;
  [ANALYTICS_EVENTS.PAGE_VIEWED]: NavigationEventProperties;
  [ANALYTICS_EVENTS.TAB_CLICKED]: NavigationEventProperties;
  [ANALYTICS_EVENTS.MODAL_OPENED]: NavigationEventProperties;
  [ANALYTICS_EVENTS.MODAL_CLOSED]: NavigationEventProperties;
  [ANALYTICS_EVENTS.ERROR_OCCURRED]: ErrorEventProperties;
  [ANALYTICS_EVENTS.API_ERROR]: ErrorEventProperties;
  [ANALYTICS_EVENTS.VALIDATION_ERROR]: ErrorEventProperties;
  [ANALYTICS_EVENTS.PASSWORD_RESET_REQUESTED]: AuthEventProperties;
  [ANALYTICS_EVENTS.PASSWORD_RESET_COMPLETED]: AuthEventProperties;
  [ANALYTICS_EVENTS.EMAIL_VERIFIED]: AuthEventProperties;
  [ANALYTICS_EVENTS.ORGANIZATION_CREATED]: OrganizationEventProperties;
  [ANALYTICS_EVENTS.ORGANIZATION_UPDATED]: OrganizationEventProperties;
  [ANALYTICS_EVENTS.TEAM_MEMBER_INVITED]: OrganizationEventProperties;
  [ANALYTICS_EVENTS.TEAM_MEMBER_REMOVED]: OrganizationEventProperties;
  [ANALYTICS_EVENTS.PROMO_CODE_REDEEMED]: PromoCodeEventProperties;
  [ANALYTICS_EVENTS.PROMO_CODE_FAILED]: PromoCodeEventProperties;
}

/**
 * Type helper to get properties for a specific event
 */
export type EventProperties<E extends AnalyticsEventName> =
  E extends keyof EventPropertiesMap
    ? EventPropertiesMap[E]
    : BaseEventProperties;
