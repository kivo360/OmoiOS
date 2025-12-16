import { test, expect } from "@playwright/test"

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
  })

  test("displays login page correctly", async ({ page }) => {
    await page.goto("/login")

    // Check page elements
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible()
  })

  test("shows validation errors for empty form", async ({ page }) => {
    await page.goto("/login")

    // Try to submit empty form
    await page.getByRole("button", { name: /sign in/i }).click()

    // Should show validation errors
    await expect(page.getByText(/email is required/i)).toBeVisible()
  })

  test("shows error for invalid credentials", async ({ page }) => {
    await page.goto("/login")

    // Fill in wrong credentials
    await page.getByLabel(/email/i).fill("wrong@example.com")
    await page.getByLabel(/password/i).fill("wrongpassword")
    await page.getByRole("button", { name: /sign in/i }).click()

    // Should show error message
    await expect(page.getByText(/invalid credentials/i)).toBeVisible()
  })

  test("successfully logs in and redirects", async ({ page }) => {
    await page.goto("/login")

    // Fill in correct credentials
    await page.getByLabel(/email/i).fill("test@example.com")
    await page.getByLabel(/password/i).fill("password123")
    await page.getByRole("button", { name: /sign in/i }).click()

    // Should redirect to dashboard/command page
    await expect(page).toHaveURL(/\/(command|dashboard)/)
  })

  test("logout clears session", async ({ page }) => {
    // First login
    await page.goto("/login")
    await page.getByLabel(/email/i).fill("test@example.com")
    await page.getByLabel(/password/i).fill("password123")
    await page.getByRole("button", { name: /sign in/i }).click()

    // Wait for redirect
    await expect(page).toHaveURL(/\/(command|dashboard)/)

    // Find and click logout (adjust selector as needed)
    await page.getByRole("button", { name: /logout|sign out/i }).click()

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/)

    // Trying to access protected route should redirect to login
    await page.goto("/command")
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe("Registration", () => {
  test("displays registration page correctly", async ({ page }) => {
    await page.goto("/register")

    await expect(
      page.getByRole("heading", { name: /create.*account|sign up|register/i })
    ).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i).first()).toBeVisible()
  })

  test("validates password requirements", async ({ page }) => {
    await page.goto("/register")

    // Fill in weak password
    await page.getByLabel(/email/i).fill("newuser@example.com")
    await page.getByLabel(/^password$/i).fill("weak")

    // Should show password requirements
    await page.getByRole("button", { name: /sign up|register|create/i }).click()

    await expect(
      page.getByText(/password.*8.*characters|too short/i)
    ).toBeVisible()
  })

  test("validates password confirmation", async ({ page }) => {
    await page.goto("/register")

    // Fill in mismatched passwords
    await page.getByLabel(/email/i).fill("newuser@example.com")
    await page.getByLabel(/^password$/i).fill("password123")
    await page.getByLabel(/confirm.*password/i).fill("different123")

    await page.getByRole("button", { name: /sign up|register|create/i }).click()

    await expect(page.getByText(/passwords.*match/i)).toBeVisible()
  })
})

test.describe("Password Reset", () => {
  test("displays forgot password page", async ({ page }) => {
    await page.goto("/forgot-password")

    await expect(
      page.getByRole("heading", { name: /forgot.*password|reset.*password/i })
    ).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
  })

  test("sends reset email and shows confirmation", async ({ page }) => {
    await page.goto("/forgot-password")

    await page.getByLabel(/email/i).fill("test@example.com")
    await page.getByRole("button", { name: /send|reset|submit/i }).click()

    // Should show success message
    await expect(
      page.getByText(/email.*sent|check.*inbox|reset.*link/i)
    ).toBeVisible()
  })
})
