import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listProjectSpecs,
  createSpec,
  getSpec,
  updateSpec,
  deleteSpec,
  addRequirement,
  updateRequirement,
  deleteRequirement,
  addCriterion,
  updateCriterion,
  updateDesign,
  approveRequirements,
  approveDesign,
} from "@/lib/api/specs"
import type {
  Spec,
  SpecListResponse,
  SpecCreate,
  SpecUpdate,
  RequirementCreate,
  RequirementUpdate,
  CriterionCreate,
  CriterionUpdate,
  DesignArtifact,
  Requirement,
  AcceptanceCriterion,
} from "@/lib/api/specs"

export const specsKeys = {
  all: ["specs"] as const,
  project: (projectId: string) => [...specsKeys.all, "project", projectId] as const,
  detail: (specId: string) => [...specsKeys.all, "detail", specId] as const,
}

/**
 * Hook to list specs for a project
 */
export function useProjectSpecs(
  projectId: string | undefined,
  params?: { status?: string }
) {
  return useQuery<SpecListResponse>({
    queryKey: specsKeys.project(projectId!),
    queryFn: () => listProjectSpecs(projectId!, params),
    enabled: !!projectId,
  })
}

/**
 * Hook to get a single spec
 */
export function useSpec(specId: string | undefined) {
  return useQuery<Spec>({
    queryKey: specsKeys.detail(specId!),
    queryFn: () => getSpec(specId!),
    enabled: !!specId,
  })
}

/**
 * Hook to create a spec
 */
export function useCreateSpec() {
  const queryClient = useQueryClient()

  return useMutation<Spec, Error, SpecCreate>({
    mutationFn: createSpec,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.project(data.project_id) })
    },
  })
}

/**
 * Hook to update a spec
 */
export function useUpdateSpec(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<Spec, Error, SpecUpdate>({
    mutationFn: (data) => updateSpec(specId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
      queryClient.invalidateQueries({ queryKey: specsKeys.project(data.project_id) })
    },
  })
}

/**
 * Hook to delete a spec
 */
export function useDeleteSpec() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, { specId: string; projectId: string }>({
    mutationFn: ({ specId }) => deleteSpec(specId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: specsKeys.project(projectId) })
    },
  })
}

/**
 * Hook to add a requirement
 */
export function useAddRequirement(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<Requirement, Error, RequirementCreate>({
    mutationFn: (data) => addRequirement(specId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update a requirement
 */
export function useUpdateRequirement(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<Requirement, Error, RequirementUpdate>({
    mutationFn: (data) => updateRequirement(specId, reqId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to delete a requirement
 */
export function useDeleteRequirement(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (reqId) => deleteRequirement(specId, reqId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to add a criterion
 */
export function useAddCriterion(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<AcceptanceCriterion, Error, CriterionCreate>({
    mutationFn: (data) => addCriterion(specId, reqId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update a criterion
 */
export function useUpdateCriterion(specId: string, reqId: string) {
  const queryClient = useQueryClient()

  return useMutation<AcceptanceCriterion, Error, { criterionId: string; data: CriterionUpdate }>({
    mutationFn: ({ criterionId, data }) => updateCriterion(specId, reqId, criterionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to update design
 */
export function useUpdateDesign(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<DesignArtifact, Error, DesignArtifact>({
    mutationFn: (design) => updateDesign(specId, design),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to approve requirements
 */
export function useApproveRequirements(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, void>({
    mutationFn: () => approveRequirements(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

/**
 * Hook to approve design
 */
export function useApproveDesign(specId: string) {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, void>({
    mutationFn: () => approveDesign(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}
