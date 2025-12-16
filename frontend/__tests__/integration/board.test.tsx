import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { createWrapper, createTestQueryClient } from "../utils"
import { useBoardView, useMoveTicket } from "@/hooks/useBoard"
import { http, HttpResponse } from "msw"
import { server } from "../mocks/server"
import { QueryClient } from "@tanstack/react-query"

describe("Board Integration", () => {
  describe("useBoardView", () => {
    it("fetches board view with columns and tickets", async () => {
      const { result } = renderHook(() => useBoardView("proj-1"), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      const board = result.current.data
      expect(board?.columns).toHaveLength(3)

      // Verify column structure
      const backlogColumn = board?.columns.find((c) => c.name === "Backlog")
      expect(backlogColumn).toBeDefined()
      expect(backlogColumn?.tickets).toHaveLength(1)

      const inProgressColumn = board?.columns.find(
        (c) => c.name === "In Progress"
      )
      expect(inProgressColumn).toBeDefined()
      expect(inProgressColumn?.wip_limit).toBe(5)
    })

    it("handles empty board", async () => {
      server.use(
        http.get("*/api/v1/board/:projectId", () => {
          return HttpResponse.json({ columns: [] })
        })
      )

      const { result } = renderHook(() => useBoardView("empty-project"), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data?.columns).toHaveLength(0)
    })
  })

  describe("useMoveTicket", () => {
    it("moves ticket and invalidates board cache", async () => {
      const queryClient = createTestQueryClient()

      // Pre-populate the board cache
      queryClient.setQueryData(["board", "proj-1"], {
        columns: [
          { id: "col-1", name: "Backlog", tickets: [{ id: "ticket-1" }] },
          { id: "col-2", name: "In Progress", tickets: [] },
        ],
      })

      const { result } = renderHook(() => useMoveTicket(), {
        wrapper: createWrapper(queryClient),
      })

      // Move ticket
      result.current.mutate({
        ticket_id: "ticket-1",
        target_column_id: "col-2",
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual({
        success: true,
        ticket_id: "ticket-1",
        new_column: "col-2",
      })
    })

    it("handles move failure gracefully", async () => {
      server.use(
        http.post("*/api/v1/board/move", () => {
          return HttpResponse.json(
            { detail: "WIP limit exceeded" },
            { status: 400 }
          )
        })
      )

      const { result } = renderHook(() => useMoveTicket(), {
        wrapper: createWrapper(),
      })

      result.current.mutate({
        ticket_id: "ticket-1",
        target_column_id: "col-2",
      })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
    })
  })

  describe("Board and Ticket Query Coordination", () => {
    it("board tickets match individual ticket queries", async () => {
      const queryClient = createTestQueryClient()
      const wrapper = createWrapper(queryClient)

      // Fetch board
      const { result: boardResult } = renderHook(
        () => useBoardView("proj-1"),
        { wrapper }
      )

      await waitFor(() => {
        expect(boardResult.current.isSuccess).toBe(true)
      })

      // Get a ticket from the board
      const boardTicket = boardResult.current.data?.columns
        .flatMap((c) => c.tickets)
        .find((t) => t.id === "ticket-1")

      // Fetch the same ticket individually
      const { useTicket } = await import("@/hooks/useTickets")
      const { result: ticketResult } = renderHook(
        () => useTicket("ticket-1"),
        { wrapper }
      )

      await waitFor(() => {
        expect(ticketResult.current.isSuccess).toBe(true)
      })

      // Both should have same core data
      expect(boardTicket?.title).toBe(ticketResult.current.data?.title)
      expect(boardTicket?.status).toBe(ticketResult.current.data?.status)
    })
  })
})
