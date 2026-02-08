import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Counter } from "@/components/ui/counter"

describe("Counter", () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("Rendering", () => {
    it("renders with default initial value of 0", () => {
      render(<Counter />)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("0")
    })

    it("renders with custom initial value", () => {
      render(<Counter initialValue={10} />)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("10")
    })

    it("renders increment, decrement, and reset buttons", () => {
      render(<Counter />)
      expect(screen.getByTestId("increment-button")).toBeInTheDocument()
      expect(screen.getByTestId("decrement-button")).toBeInTheDocument()
      expect(screen.getByTestId("reset-button")).toBeInTheDocument()
    })

    it("renders with accessible labels", () => {
      render(<Counter />)
      expect(screen.getByLabelText("Increment")).toBeInTheDocument()
      expect(screen.getByLabelText("Decrement")).toBeInTheDocument()
      expect(screen.getByLabelText("Reset")).toBeInTheDocument()
    })
  })

  describe("Increment", () => {
    it("increments the count by 1 by default", async () => {
      render(<Counter />)
      const incrementButton = screen.getByTestId("increment-button")

      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("1")

      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("2")
    })

    it("increments by custom step value", async () => {
      render(<Counter step={5} />)
      const incrementButton = screen.getByTestId("increment-button")

      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("5")
    })

    it("does not exceed max value", async () => {
      render(<Counter initialValue={9} max={10} />)
      const incrementButton = screen.getByTestId("increment-button")

      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("10")

      // Button should be disabled at max
      expect(incrementButton).toBeDisabled()
    })
  })

  describe("Decrement", () => {
    it("decrements the count by 1 by default", async () => {
      render(<Counter initialValue={5} />)
      const decrementButton = screen.getByTestId("decrement-button")

      await user.click(decrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("4")

      await user.click(decrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("3")
    })

    it("decrements by custom step value", async () => {
      render(<Counter initialValue={10} step={3} />)
      const decrementButton = screen.getByTestId("decrement-button")

      await user.click(decrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("7")
    })

    it("does not go below min value", async () => {
      render(<Counter initialValue={1} min={0} />)
      const decrementButton = screen.getByTestId("decrement-button")

      await user.click(decrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("0")

      // Button should be disabled at min
      expect(decrementButton).toBeDisabled()
    })
  })

  describe("Reset", () => {
    it("resets the count to initial value", async () => {
      render(<Counter initialValue={5} />)
      const incrementButton = screen.getByTestId("increment-button")
      const resetButton = screen.getByTestId("reset-button")

      // Increment a few times
      await user.click(incrementButton)
      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("7")

      // Reset
      await user.click(resetButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("5")
    })

    it("resets to 0 when no initial value provided", async () => {
      render(<Counter />)
      const incrementButton = screen.getByTestId("increment-button")
      const resetButton = screen.getByTestId("reset-button")

      await user.click(incrementButton)
      await user.click(incrementButton)
      await user.click(incrementButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("3")

      await user.click(resetButton)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("0")
    })
  })

  describe("onChange callback", () => {
    it("calls onChange when count is incremented", async () => {
      const onChange = vi.fn()
      render(<Counter onChange={onChange} />)
      const incrementButton = screen.getByTestId("increment-button")

      await user.click(incrementButton)
      expect(onChange).toHaveBeenCalledWith(1)
    })

    it("calls onChange when count is decremented", async () => {
      const onChange = vi.fn()
      render(<Counter initialValue={5} onChange={onChange} />)
      const decrementButton = screen.getByTestId("decrement-button")

      await user.click(decrementButton)
      expect(onChange).toHaveBeenCalledWith(4)
    })

    it("calls onChange when count is reset", async () => {
      const onChange = vi.fn()
      render(<Counter initialValue={5} onChange={onChange} />)
      const incrementButton = screen.getByTestId("increment-button")
      const resetButton = screen.getByTestId("reset-button")

      await user.click(incrementButton)
      await user.click(resetButton)
      expect(onChange).toHaveBeenLastCalledWith(5)
    })
  })

  describe("Boundary conditions", () => {
    it("handles negative initial values", () => {
      render(<Counter initialValue={-5} />)
      expect(screen.getByTestId("counter-display")).toHaveTextContent("-5")
    })

    it("respects min and max boundaries on initial value", () => {
      render(<Counter initialValue={100} min={0} max={10} />)
      // Initial value should be displayed even if out of bounds
      // But subsequent operations should clamp
      expect(screen.getByTestId("counter-display")).toHaveTextContent("100")
    })
  })
})
