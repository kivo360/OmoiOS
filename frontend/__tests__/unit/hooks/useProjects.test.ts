import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { createWrapper } from "../../utils"
import { useProjects, useProject, useProjectStats } from "@/hooks/useProjects"
import { mockProjects, mockProjectStats } from "../../mocks/handlers"

describe("useProjects hook", () => {
  it("fetches projects successfully", async () => {
    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    })

    // Initially loading
    expect(result.current.isLoading).toBe(true)

    // Wait for data
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    // Verify data
    expect(result.current.data?.projects).toHaveLength(2)
    expect(result.current.data?.projects[0].name).toBe("OmoiOS")
  })

  it("returns correct total count", async () => {
    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.total).toBe(2)
  })
})

describe("useProject hook", () => {
  it("fetches single project by id", async () => {
    const { result } = renderHook(() => useProject("proj-1"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.name).toBe("OmoiOS")
    expect(result.current.data?.github_connected).toBe(true)
  })

  it("handles non-existent project", async () => {
    const { result } = renderHook(() => useProject("non-existent"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })
  })

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useProject(""), {
      wrapper: createWrapper(),
    })

    // Should not be loading because query is disabled
    expect(result.current.fetchStatus).toBe("idle")
  })
})

describe("useProjectStats hook", () => {
  it("fetches project stats", async () => {
    const { result } = renderHook(() => useProjectStats("proj-1"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.total_tickets).toBe(25)
    expect(result.current.data?.active_agents).toBe(3)
    expect(result.current.data?.tickets_by_status).toHaveProperty("in_progress")
  })
})
