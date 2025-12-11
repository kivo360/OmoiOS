/**
 * Organizations API functions
 */

import { apiRequest } from "./client"
import type {
  Organization,
  OrganizationSummary,
  OrganizationCreate,
  OrganizationUpdate,
  Role,
  RoleCreate,
  Membership,
  MembershipCreate,
  MessageResponse,
} from "./types"

// ============================================================================
// Organizations
// ============================================================================

/**
 * List all organizations the current user is a member of
 */
export async function listOrganizations(): Promise<OrganizationSummary[]> {
  return apiRequest<OrganizationSummary[]>("/api/v1/organizations")
}

/**
 * Get organization details
 */
export async function getOrganization(orgId: string): Promise<Organization> {
  return apiRequest<Organization>(`/api/v1/organizations/${orgId}`)
}

/**
 * Create a new organization
 */
export async function createOrganization(
  data: OrganizationCreate
): Promise<Organization> {
  return apiRequest<Organization>("/api/v1/organizations", {
    method: "POST",
    body: data,
  })
}

/**
 * Update organization
 */
export async function updateOrganization(
  orgId: string,
  data: OrganizationUpdate
): Promise<Organization> {
  return apiRequest<Organization>(`/api/v1/organizations/${orgId}`, {
    method: "PATCH",
    body: data,
  })
}

/**
 * Delete (archive) organization
 */
export async function deleteOrganization(orgId: string): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(`/api/v1/organizations/${orgId}`, {
    method: "DELETE",
  })
}

// ============================================================================
// Members
// ============================================================================

/**
 * List organization members
 */
export async function listMembers(orgId: string): Promise<Membership[]> {
  return apiRequest<Membership[]>(`/api/v1/organizations/${orgId}/members`)
}

/**
 * Add member to organization
 */
export async function addMember(
  orgId: string,
  data: MembershipCreate
): Promise<Membership> {
  return apiRequest<Membership>(`/api/v1/organizations/${orgId}/members`, {
    method: "POST",
    body: data,
  })
}

/**
 * Update member role
 */
export async function updateMember(
  orgId: string,
  memberId: string,
  roleId: string
): Promise<Membership> {
  return apiRequest<Membership>(
    `/api/v1/organizations/${orgId}/members/${memberId}`,
    {
      method: "PATCH",
      body: { role_id: roleId },
    }
  )
}

/**
 * Remove member from organization
 */
export async function removeMember(
  orgId: string,
  memberId: string
): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    `/api/v1/organizations/${orgId}/members/${memberId}`,
    { method: "DELETE" }
  )
}

// ============================================================================
// Roles
// ============================================================================

/**
 * List roles available in organization
 */
export async function listRoles(
  orgId: string,
  includeSystem = true
): Promise<Role[]> {
  const url = `/api/v1/organizations/${orgId}/roles?include_system=${includeSystem}`
  return apiRequest<Role[]>(url)
}

/**
 * Create custom role for organization
 */
export async function createRole(
  orgId: string,
  data: Omit<RoleCreate, "organization_id">
): Promise<Role> {
  return apiRequest<Role>(`/api/v1/organizations/${orgId}/roles`, {
    method: "POST",
    body: { ...data, organization_id: orgId },
  })
}

/**
 * Update role
 */
export async function updateRole(
  orgId: string,
  roleId: string,
  data: Partial<Omit<RoleCreate, "organization_id">>
): Promise<Role> {
  return apiRequest<Role>(`/api/v1/organizations/${orgId}/roles/${roleId}`, {
    method: "PATCH",
    body: data,
  })
}

/**
 * Delete custom role
 */
export async function deleteRole(
  orgId: string,
  roleId: string
): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    `/api/v1/organizations/${orgId}/roles/${roleId}`,
    { method: "DELETE" }
  )
}
