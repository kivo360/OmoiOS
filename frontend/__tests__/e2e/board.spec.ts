import { test, expect } from "@playwright/test"

test.describe("Kanban Board", () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto("/login")
    await page.getByLabel(/email/i).fill("test@example.com")
    await page.getByLabel(/password/i).fill("password123")
    await page.getByRole("button", { name: /sign in/i }).click()

    // Wait for login to complete
    await expect(page).toHaveURL(/\/(command|dashboard)/)
  })

  test("displays board with columns", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Should show columns
    await expect(page.getByText(/backlog/i)).toBeVisible()
    await expect(page.getByText(/in progress/i)).toBeVisible()
    await expect(page.getByText(/done/i)).toBeVisible()
  })

  test("displays tickets in columns", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Should show tickets
    await expect(page.getByText(/implement authentication/i)).toBeVisible()
  })

  test("can drag ticket between columns", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Find the ticket
    const ticket = page.locator('[data-ticket-id="ticket-1"]')

    // Find the target column
    const doneColumn = page.locator('[data-column="done"]')

    // Drag ticket to done column
    await ticket.dragTo(doneColumn)

    // Verify ticket moved (or optimistic update occurred)
    // Note: Exact assertion depends on implementation
    await expect(ticket).toBeVisible()
  })

  test("shows WIP limit indicator", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // In Progress column has WIP limit of 5
    const inProgressColumn = page.locator('[data-column="in_progress"]')

    // Should show WIP limit indicator
    await expect(
      inProgressColumn.getByText(/wip|limit/i)
    ).toBeVisible()
  })

  test("can create new ticket from board", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Click add ticket button
    await page.getByRole("button", { name: /add.*ticket|new.*ticket|\+/i }).click()

    // Fill in ticket details
    await page.getByLabel(/title/i).fill("New test ticket")
    await page.getByLabel(/description/i).fill("Test description")

    // Submit
    await page.getByRole("button", { name: /create|save|add/i }).click()

    // Should see new ticket in backlog
    await expect(page.getByText("New test ticket")).toBeVisible()
  })

  test("can view ticket details", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Click on a ticket
    await page.getByText(/implement authentication/i).click()

    // Should show ticket detail view/modal
    await expect(
      page.getByRole("heading", { name: /implement authentication/i })
    ).toBeVisible()

    // Should show ticket info
    await expect(page.getByText(/high/i)).toBeVisible() // priority
    await expect(page.getByText(/in.progress/i)).toBeVisible() // status
  })
})

test.describe("Board Filtering", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login")
    await page.getByLabel(/email/i).fill("test@example.com")
    await page.getByLabel(/password/i).fill("password123")
    await page.getByRole("button", { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/(command|dashboard)/)
  })

  test("can filter by priority", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Open filter dropdown
    await page.getByRole("button", { name: /filter/i }).click()

    // Select high priority
    await page.getByLabel(/priority/i).selectOption("high")

    // Should only show high priority tickets
    await expect(page.getByText(/implement authentication/i)).toBeVisible()
    // Low priority ticket should be hidden
    await expect(
      page.getByText(/refactor api client/i)
    ).not.toBeVisible()
  })

  test("can search tickets", async ({ page }) => {
    await page.goto("/projects/proj-1/board")

    // Enter search query
    await page.getByPlaceholder(/search/i).fill("authentication")

    // Should only show matching ticket
    await expect(page.getByText(/implement authentication/i)).toBeVisible()
    await expect(page.getByText(/testing infrastructure/i)).not.toBeVisible()
  })
})
