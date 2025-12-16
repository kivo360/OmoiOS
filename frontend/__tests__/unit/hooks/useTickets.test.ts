import { describe, it, expect } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { createWrapper } from "../../utils"
import { useTickets, useTicket } from "@/hooks/useTickets"

describe("useTickets hook", () => {
  it("fetches tickets successfully", async () => {
    const { result } = renderHook(() => useTickets(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.tickets).toBeDefined()
    expect(result.current.data?.tickets.length).toBeGreaterThan(0)
  })

  it("fetches tickets with project filter", async () => {
    const { result } = renderHook(
      () => useTickets({ project_id: "proj-1" }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    // All tickets should belong to the filtered project
    result.current.data?.tickets.forEach((ticket) => {
      expect(ticket.project_id).toBe("proj-1")
    })
  })
})

describe("useTicket hook", () => {
  it("fetches single ticket by id", async () => {
    const { result } = renderHook(() => useTicket("ticket-1"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.title).toBe("Implement authentication")
    expect(result.current.data?.status).toBe("in_progress")
    expect(result.current.data?.priority).toBe("high")
  })

  it("handles non-existent ticket", async () => {
    const { result } = renderHook(() => useTicket("non-existent"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })
  })
})
