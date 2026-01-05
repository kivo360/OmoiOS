/**
 * User Identification Module
 *
 * Handles user identification and properties for PostHog.
 * This links anonymous sessions to identified users.
 */

import { posthog, isPostHogReady } from './posthog'
import type { User } from '@/lib/api/types'

/**
 * User properties that can be set in PostHog
 */
export interface UserProperties {
  email?: string
  name?: string
  full_name?: string
  plan_type?: 'free' | 'pro' | 'team' | 'enterprise' | 'lifetime'
  organization_id?: string
  organization_name?: string
  github_connected?: boolean
  github_username?: string
  is_verified?: boolean
  created_at?: string
  onboarding_completed?: boolean
  subscription_tier?: string
  [key: string]: unknown
}

/**
 * Identify a user in PostHog
 * This links all previous anonymous events to this user
 *
 * @param userId - Unique user identifier (typically user.id)
 * @param properties - User properties to set
 *
 * @example
 * ```ts
 * identify(user.id, {
 *   email: user.email,
 *   name: user.full_name,
 *   plan_type: 'pro',
 * })
 * ```
 */
export function identify(userId: string, properties?: UserProperties): void {
  if (!isPostHogReady()) {
    console.log('[Analytics] Identify called but PostHog not ready:', userId)
    return
  }

  // Remove undefined values from properties
  const cleanProperties = properties
    ? Object.fromEntries(
        Object.entries(properties).filter(([, value]) => value !== undefined)
      )
    : undefined

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Identify user:', userId, cleanProperties)
  }

  posthog.identify(userId, cleanProperties)
}

/**
 * Identify a user from the User object
 * Convenience method that extracts relevant properties from the User type
 *
 * @param user - User object from the API
 * @param additionalProperties - Extra properties to merge
 */
export function identifyUser(user: User, additionalProperties?: UserProperties): void {
  const properties: UserProperties = {
    email: user.email,
    name: user.full_name || undefined,
    full_name: user.full_name || undefined,
    is_verified: user.is_verified,
    created_at: user.created_at,
    ...additionalProperties,
  }

  identify(user.id, properties)
}

/**
 * Reset the current user
 * Call this on logout to clear user identity
 */
export function resetUser(): void {
  if (!isPostHogReady()) return

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Reset user (logout)')
  }

  posthog.reset()
}

/**
 * Set user properties without identifying
 * Use this to update properties for an already identified user
 *
 * @param properties - Properties to set/update
 */
export function setUserProperties(properties: UserProperties): void {
  if (!isPostHogReady()) return

  const cleanProperties = Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined)
  )

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Set user properties:', cleanProperties)
  }

  posthog.setPersonProperties(cleanProperties)
}

/**
 * Set properties that persist across all events for this user
 * These "super properties" are included with every event
 *
 * @param properties - Properties to persist
 */
export function setSuperProperties(properties: Record<string, unknown>): void {
  if (!isPostHogReady()) return

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Set super properties:', properties)
  }

  posthog.register(properties)
}

/**
 * Remove super properties
 *
 * @param propertyNames - Names of properties to remove
 */
export function unsetSuperProperties(propertyNames: string[]): void {
  if (!isPostHogReady()) return

  propertyNames.forEach((name) => {
    posthog.unregister(name)
  })
}

/**
 * Alias an anonymous ID to a user ID
 * Useful for linking pre-signup activity to a new user
 *
 * @param alias - The alias to create (typically the new user ID)
 */
export function aliasUser(alias: string): void {
  if (!isPostHogReady()) return

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Alias user:', alias)
  }

  posthog.alias(alias)
}

/**
 * Group a user into an organization/company
 * Useful for B2B analytics
 *
 * @param groupType - Type of group (e.g., 'organization', 'company')
 * @param groupKey - Unique identifier for the group
 * @param properties - Properties of the group
 */
export function setGroup(
  groupType: string,
  groupKey: string,
  properties?: Record<string, unknown>
): void {
  if (!isPostHogReady()) return

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Set group:', groupType, groupKey, properties)
  }

  posthog.group(groupType, groupKey, properties)
}

/**
 * Organization properties for group analytics
 */
export interface OrganizationProperties {
  name?: string
  slug?: string
  plan_type?: 'free' | 'pro' | 'team' | 'enterprise' | 'lifetime'
  member_count?: number
  created_at?: string
  billing_email?: string
  [key: string]: unknown
}

/**
 * Set the current organization context
 * All events will be associated with this organization
 *
 * @param organizationId - Organization ID
 * @param properties - Organization properties
 */
export function setOrganization(
  organizationId: string,
  properties?: OrganizationProperties
): void {
  setGroup('organization', organizationId, properties)

  // Also set as a super property for easy filtering
  if (isPostHogReady()) {
    posthog.register({
      organization_id: organizationId,
      organization_name: properties?.name,
    })
  }

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Set organization:', organizationId, properties)
  }
}

/**
 * Clear the organization context
 * Call when switching organizations or logging out
 */
export function clearOrganization(): void {
  if (!isPostHogReady()) return

  posthog.resetGroups()
  posthog.unregister('organization_id')
  posthog.unregister('organization_name')

  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics] Cleared organization context')
  }
}
