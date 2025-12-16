import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "../../utils"
import { Button } from "@/components/ui/button"

describe("Button component", () => {
  it("renders with default variant", () => {
    render(<Button>Click me</Button>)

    const button = screen.getByRole("button", { name: /click me/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass("bg-primary")
  })

  it("renders with destructive variant", () => {
    render(<Button variant="destructive">Delete</Button>)

    const button = screen.getByRole("button", { name: /delete/i })
    expect(button).toHaveClass("bg-destructive")
  })

  it("renders with outline variant", () => {
    render(<Button variant="outline">Outline</Button>)

    const button = screen.getByRole("button", { name: /outline/i })
    expect(button).toHaveClass("border")
    expect(button).toHaveClass("bg-background")
  })

  it("renders with ghost variant", () => {
    render(<Button variant="ghost">Ghost</Button>)

    const button = screen.getByRole("button", { name: /ghost/i })
    expect(button).not.toHaveClass("bg-primary")
    expect(button).not.toHaveClass("border")
  })

  it("renders with different sizes", () => {
    const { rerender } = render(<Button size="sm">Small</Button>)
    expect(screen.getByRole("button")).toHaveClass("h-8")

    rerender(<Button size="lg">Large</Button>)
    expect(screen.getByRole("button")).toHaveClass("h-10")

    rerender(<Button size="icon">Icon</Button>)
    expect(screen.getByRole("button")).toHaveClass("h-9", "w-9")
  })

  it("handles click events", () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)

    fireEvent.click(screen.getByRole("button"))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it("can be disabled", () => {
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    )

    const button = screen.getByRole("button")
    expect(button).toBeDisabled()
    expect(button).toHaveClass("disabled:opacity-50")

    fireEvent.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })

  it("renders as child component when asChild is true", () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    )

    const link = screen.getByRole("link", { name: /link button/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/test")
  })

  it("applies custom className", () => {
    render(<Button className="custom-class">Custom</Button>)

    expect(screen.getByRole("button")).toHaveClass("custom-class")
  })
})
