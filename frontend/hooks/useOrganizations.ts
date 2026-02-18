/**
 * React Query hooks for Organizations API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listOrganizations,
  getOrganization,
  createOrganization,
  updateOrganization,
  deleteOrganization,
  listMembers,
  addMember,
  updateMember,
  removeMember,
  listRoles,
  createRole,
  updateRole,
  deleteRole,
} from "@/lib/api/organizations";
import type {
  Organization,
  OrganizationSummary,
  OrganizationCreate,
  OrganizationUpdate,
  Role,
  RoleCreate,
  Membership,
  MembershipCreate,
} from "@/lib/api/types";

// UUID validation regex - prevents API calls with invalid IDs like "new"
const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Check if a string is a valid UUID
 */
function isValidUUID(id: string | undefined): id is string {
  return !!id && UUID_REGEX.test(id);
}

// Query keys
export const organizationKeys = {
  all: ["organizations"] as const,
  lists: () => [...organizationKeys.all, "list"] as const,
  details: () => [...organizationKeys.all, "detail"] as const,
  detail: (id: string) => [...organizationKeys.details(), id] as const,
  members: (orgId: string) =>
    [...organizationKeys.detail(orgId), "members"] as const,
  roles: (orgId: string) =>
    [...organizationKeys.detail(orgId), "roles"] as const,
};

// ============================================================================
// Organization Hooks
// ============================================================================

/**
 * Hook to fetch list of organizations user belongs to
 */
export function useOrganizations() {
  return useQuery<OrganizationSummary[]>({
    queryKey: organizationKeys.lists(),
    queryFn: listOrganizations,
  });
}

/**
 * Hook to fetch a single organization
 */
export function useOrganization(orgId: string | undefined) {
  return useQuery<Organization>({
    queryKey: organizationKeys.detail(orgId!),
    queryFn: () => getOrganization(orgId!),
    enabled: isValidUUID(orgId),
  });
}

/**
 * Hook to create an organization
 */
export function useCreateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: OrganizationCreate) => createOrganization(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: organizationKeys.lists() });
    },
  });
}

/**
 * Hook to update an organization
 */
export function useUpdateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orgId,
      data,
    }: {
      orgId: string;
      data: OrganizationUpdate;
    }) => updateOrganization(orgId, data),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.detail(orgId),
      });
      queryClient.invalidateQueries({ queryKey: organizationKeys.lists() });
    },
  });
}

/**
 * Hook to delete an organization
 */
export function useDeleteOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orgId: string) => deleteOrganization(orgId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: organizationKeys.lists() });
    },
  });
}

// ============================================================================
// Member Hooks
// ============================================================================

/**
 * Hook to fetch organization members
 */
export function useMembers(orgId: string | undefined) {
  return useQuery<Membership[]>({
    queryKey: organizationKeys.members(orgId!),
    queryFn: () => listMembers(orgId!),
    enabled: isValidUUID(orgId),
  });
}

/**
 * Hook to add a member
 */
export function useAddMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orgId, data }: { orgId: string; data: MembershipCreate }) =>
      addMember(orgId, data),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.members(orgId),
      });
    },
  });
}

/**
 * Hook to update member role
 */
export function useUpdateMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orgId,
      memberId,
      roleId,
    }: {
      orgId: string;
      memberId: string;
      roleId: string;
    }) => updateMember(orgId, memberId, roleId),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.members(orgId),
      });
    },
  });
}

/**
 * Hook to remove a member
 */
export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orgId, memberId }: { orgId: string; memberId: string }) =>
      removeMember(orgId, memberId),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.members(orgId),
      });
    },
  });
}

// ============================================================================
// Role Hooks
// ============================================================================

/**
 * Hook to fetch organization roles
 */
export function useRoles(orgId: string | undefined, includeSystem = true) {
  return useQuery<Role[]>({
    queryKey: organizationKeys.roles(orgId!),
    queryFn: () => listRoles(orgId!, includeSystem),
    enabled: isValidUUID(orgId),
  });
}

/**
 * Hook to create a role
 */
export function useCreateRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orgId,
      data,
    }: {
      orgId: string;
      data: Omit<RoleCreate, "organization_id">;
    }) => createRole(orgId, data),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.roles(orgId),
      });
    },
  });
}

/**
 * Hook to update a role
 */
export function useUpdateRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      orgId,
      roleId,
      data,
    }: {
      orgId: string;
      roleId: string;
      data: Partial<Omit<RoleCreate, "organization_id">>;
    }) => updateRole(orgId, roleId, data),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.roles(orgId),
      });
    },
  });
}

/**
 * Hook to delete a role
 */
export function useDeleteRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orgId, roleId }: { orgId: string; roleId: string }) =>
      deleteRole(orgId, roleId),
    onSuccess: (_, { orgId }) => {
      queryClient.invalidateQueries({
        queryKey: organizationKeys.roles(orgId),
      });
    },
  });
}
