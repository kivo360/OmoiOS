import { describe, it, expect } from "vitest"
import { render, screen } from "../../utils"
import { AgentCard, AgentStatus } from "@/components/custom/AgentCard"

describe("AgentCard component", () => {
  const defaultProps = {
    id: "agent-1",
    taskName: "Implement authentication",
    status: "running" as AgentStatus,
    timeAgo: "5m ago",
  }

  it("renders task name and time", () => {
    render(<AgentCard {...defaultProps} />)

    expect(screen.getByText("Implement authentication")).toBeInTheDocument()
    expect(screen.getByText("5m ago")).toBeInTheDocument()
  })

  it("renders as a link to agent detail page", () => {
    render(<AgentCard {...defaultProps} />)

    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "/agents/agent-1")
  })

  it("shows running status with spinner icon", () => {
    render(<AgentCard {...defaultProps} status="running" />)

    // The Loader2 icon should have animate-spin class
    const icon = document.querySelector(".animate-spin")
    expect(icon).toBeInTheDocument()
  })

  it("shows completed status with check icon", () => {
    render(<AgentCard {...defaultProps} status="completed" />)

    const icon = document.querySelector(".text-success")
    expect(icon).toBeInTheDocument()
  })

  it("shows failed status with X icon", () => {
    render(<AgentCard {...defaultProps} status="failed" />)

    const icon = document.querySelector(".text-destructive")
    expect(icon).toBeInTheDocument()
  })

  it("shows blocked status with alert icon", () => {
    render(<AgentCard {...defaultProps} status="blocked" />)

    // Blocked uses text-warning class
    const icon = document.querySelector(".text-warning")
    expect(icon).toBeInTheDocument()
  })

  it("displays line changes when provided", () => {
    render(
      <AgentCard
        {...defaultProps}
        additions={25}
        deletions={10}
      />
    )

    // LineChanges component should show additions and deletions
    expect(screen.getByText("+25")).toBeInTheDocument()
    expect(screen.getByText("-10")).toBeInTheDocument()
  })

  it("displays repo name when provided", () => {
    render(
      <AgentCard
        {...defaultProps}
        repoName="kivo360/OmoiOS"
      />
    )

    expect(screen.getByText("kivo360/OmoiOS")).toBeInTheDocument()
  })

  it("displays both line changes and repo name", () => {
    render(
      <AgentCard
        {...defaultProps}
        additions={15}
        deletions={5}
        repoName="kivo360/OmoiOS"
      />
    )

    expect(screen.getByText("+15")).toBeInTheDocument()
    expect(screen.getByText("-5")).toBeInTheDocument()
    expect(screen.getByText("kivo360/OmoiOS")).toBeInTheDocument()
    // Separator dot should be present
    expect(screen.getByText("•")).toBeInTheDocument()
  })

  it("does not show second row when no changes or repo", () => {
    render(<AgentCard {...defaultProps} />)

    // No additions, deletions, or repoName - second row should not render
    expect(screen.queryByText("•")).not.toBeInTheDocument()
  })

  it("applies custom className", () => {
    render(<AgentCard {...defaultProps} className="custom-class" />)

    const link = screen.getByRole("link")
    expect(link).toHaveClass("custom-class")
  })
})
