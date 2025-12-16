import { describe, it, expect, beforeEach } from "vitest"
import { create } from "zustand"
import { immer } from "zustand/middleware/immer"

/**
 * Example store test file demonstrating how to test Zustand stores.
 *
 * This file provides patterns for testing stores that you'll create
 * for kanban, agents, and UI state management.
 */

// Example store definition (similar to what you'd create in stores/)
interface CounterState {
  count: number
  increment: () => void
  decrement: () => void
  reset: () => void
  incrementBy: (amount: number) => void
}

const createCounterStore = () =>
  create<CounterState>()(
    immer((set) => ({
      count: 0,
      increment: () => set((state) => { state.count += 1 }),
      decrement: () => set((state) => { state.count -= 1 }),
      reset: () => set((state) => { state.count = 0 }),
      incrementBy: (amount) => set((state) => { state.count += amount }),
    }))
  )

// Example: UI Store pattern (sidebar, modals, theme)
interface UIState {
  sidebarOpen: boolean
  activeModal: string | null
  toggleSidebar: () => void
  openModal: (modalId: string) => void
  closeModal: () => void
}

const createUIStore = () =>
  create<UIState>()(
    immer((set) => ({
      sidebarOpen: true,
      activeModal: null,
      toggleSidebar: () =>
        set((state) => {
          state.sidebarOpen = !state.sidebarOpen
        }),
      openModal: (modalId) =>
        set((state) => {
          state.activeModal = modalId
        }),
      closeModal: () =>
        set((state) => {
          state.activeModal = null
        }),
    }))
  )

// Example: Kanban Store pattern
interface KanbanState {
  columns: { id: string; name: string; ticketIds: string[] }[]
  draggedTicketId: string | null
  setDraggedTicket: (id: string | null) => void
  moveTicket: (ticketId: string, fromColumn: string, toColumn: string) => void
}

const createKanbanStore = () =>
  create<KanbanState>()(
    immer((set) => ({
      columns: [
        { id: "backlog", name: "Backlog", ticketIds: ["t1", "t2"] },
        { id: "in_progress", name: "In Progress", ticketIds: ["t3"] },
        { id: "done", name: "Done", ticketIds: [] },
      ],
      draggedTicketId: null,
      setDraggedTicket: (id) =>
        set((state) => {
          state.draggedTicketId = id
        }),
      moveTicket: (ticketId, fromColumn, toColumn) =>
        set((state) => {
          const from = state.columns.find((c) => c.id === fromColumn)
          const to = state.columns.find((c) => c.id === toColumn)
          if (from && to) {
            from.ticketIds = from.ticketIds.filter((id) => id !== ticketId)
            to.ticketIds.push(ticketId)
          }
        }),
    }))
  )

describe("Counter Store Example", () => {
  let useStore: ReturnType<typeof createCounterStore>

  beforeEach(() => {
    // Create fresh store for each test
    useStore = createCounterStore()
  })

  it("has initial count of 0", () => {
    expect(useStore.getState().count).toBe(0)
  })

  it("increments count", () => {
    useStore.getState().increment()
    expect(useStore.getState().count).toBe(1)
  })

  it("decrements count", () => {
    useStore.getState().increment()
    useStore.getState().increment()
    useStore.getState().decrement()
    expect(useStore.getState().count).toBe(1)
  })

  it("resets count to 0", () => {
    useStore.getState().incrementBy(10)
    useStore.getState().reset()
    expect(useStore.getState().count).toBe(0)
  })

  it("increments by specific amount", () => {
    useStore.getState().incrementBy(5)
    expect(useStore.getState().count).toBe(5)
  })
})

describe("UI Store Example", () => {
  let useStore: ReturnType<typeof createUIStore>

  beforeEach(() => {
    useStore = createUIStore()
  })

  it("has sidebar open by default", () => {
    expect(useStore.getState().sidebarOpen).toBe(true)
  })

  it("toggles sidebar state", () => {
    useStore.getState().toggleSidebar()
    expect(useStore.getState().sidebarOpen).toBe(false)

    useStore.getState().toggleSidebar()
    expect(useStore.getState().sidebarOpen).toBe(true)
  })

  it("opens and closes modals", () => {
    expect(useStore.getState().activeModal).toBeNull()

    useStore.getState().openModal("settings")
    expect(useStore.getState().activeModal).toBe("settings")

    useStore.getState().closeModal()
    expect(useStore.getState().activeModal).toBeNull()
  })

  it("replaces current modal when opening new one", () => {
    useStore.getState().openModal("settings")
    useStore.getState().openModal("confirm")
    expect(useStore.getState().activeModal).toBe("confirm")
  })
})

describe("Kanban Store Example", () => {
  let useStore: ReturnType<typeof createKanbanStore>

  beforeEach(() => {
    useStore = createKanbanStore()
  })

  it("has initial columns with tickets", () => {
    const state = useStore.getState()
    expect(state.columns).toHaveLength(3)
    expect(state.columns[0].ticketIds).toContain("t1")
    expect(state.columns[0].ticketIds).toContain("t2")
  })

  it("tracks dragged ticket", () => {
    useStore.getState().setDraggedTicket("t1")
    expect(useStore.getState().draggedTicketId).toBe("t1")

    useStore.getState().setDraggedTicket(null)
    expect(useStore.getState().draggedTicketId).toBeNull()
  })

  it("moves ticket between columns", () => {
    useStore.getState().moveTicket("t1", "backlog", "in_progress")

    const state = useStore.getState()
    const backlog = state.columns.find((c) => c.id === "backlog")!
    const inProgress = state.columns.find((c) => c.id === "in_progress")!

    expect(backlog.ticketIds).not.toContain("t1")
    expect(inProgress.ticketIds).toContain("t1")
  })

  it("handles moving ticket that does not exist gracefully", () => {
    // Should not throw
    useStore.getState().moveTicket("nonexistent", "backlog", "done")

    // State should remain unchanged
    const backlog = useStore.getState().columns.find((c) => c.id === "backlog")!
    expect(backlog.ticketIds).toEqual(["t1", "t2"])
  })

  it("handles moving to non-existent column gracefully", () => {
    useStore.getState().moveTicket("t1", "backlog", "nonexistent")

    // Ticket should still be in backlog since target doesn't exist
    const backlog = useStore.getState().columns.find((c) => c.id === "backlog")!
    expect(backlog.ticketIds).toContain("t1")
  })
})

describe("Store Selectors", () => {
  it("can use selectors for derived state", () => {
    const useStore = createKanbanStore()

    // Example selector: count tickets by column
    const getTicketCount = (columnId: string) => {
      const column = useStore.getState().columns.find((c) => c.id === columnId)
      return column?.ticketIds.length ?? 0
    }

    expect(getTicketCount("backlog")).toBe(2)
    expect(getTicketCount("in_progress")).toBe(1)
    expect(getTicketCount("done")).toBe(0)
  })

  it("can compute total tickets across all columns", () => {
    const useStore = createKanbanStore()

    const getTotalTickets = () =>
      useStore.getState().columns.reduce((sum, col) => sum + col.ticketIds.length, 0)

    expect(getTotalTickets()).toBe(3)
  })
})
