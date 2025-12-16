import { describe, it, expect, beforeEach } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "../mocks/server"

/**
 * Integration tests for authentication flows
 * These tests verify that API functions work correctly with MSW mocks
 */

describe("Authentication Flow Integration", () => {
  beforeEach(() => {
    // Clear any stored tokens
    localStorage.clear()
  })

  describe("Login", () => {
    it("successfully logs in with valid credentials", async () => {
      const { login } = await import("@/lib/api/auth")

      const result = await login({
        email: "test@example.com",
        password: "password123",
      })

      expect(result.access_token).toBe("mock-access-token")
      expect(result.refresh_token).toBe("mock-refresh-token")

      // Verify tokens were stored
      expect(localStorage.getItem("omoios_access_token")).toBe("mock-access-token")
    })

    it("fails with invalid credentials", async () => {
      const { login } = await import("@/lib/api/auth")

      await expect(
        login({
          email: "wrong@example.com",
          password: "wrongpassword",
        })
      ).rejects.toThrow()
    })
  })

  describe("Registration", () => {
    it("successfully registers a new user", async () => {
      // Override handler to return a user object for register
      server.use(
        http.post("*/api/v1/auth/register", () => {
          return HttpResponse.json({
            id: "new-user-id",
            email: "newuser@example.com",
            full_name: "New User",
            is_active: true,
            is_verified: false,
            is_super_admin: false,
            avatar_url: null,
            attributes: null,
            department: null,
            created_at: new Date().toISOString(),
            last_login_at: null,
          }, { status: 201 })
        })
      )

      const { register } = await import("@/lib/api/auth")

      const result = await register({
        email: "newuser@example.com",
        password: "password123",
      })

      expect(result.id).toBeDefined()
      expect(result.email).toBe("newuser@example.com")
    })

    it("fails when email already exists", async () => {
      server.use(
        http.post("*/api/v1/auth/register", () => {
          return HttpResponse.json(
            { detail: "Email already registered" },
            { status: 400 }
          )
        })
      )

      const { register } = await import("@/lib/api/auth")

      await expect(
        register({
          email: "existing@example.com",
          password: "password123",
        })
      ).rejects.toThrow()
    })
  })

  describe("Password Reset", () => {
    it("successfully sends password reset email", async () => {
      const { forgotPassword } = await import("@/lib/api/auth")

      const result = await forgotPassword({ email: "test@example.com" })

      expect(result.message).toBe("Password reset email sent")
    })

    it("successfully resets password with valid token", async () => {
      const { resetPassword } = await import("@/lib/api/auth")

      const result = await resetPassword({
        token: "valid-reset-token",
        new_password: "newpassword123",
      })

      expect(result.message).toBe("Password reset successful")
    })
  })

  describe("Get Current User", () => {
    it("fetches current user profile", async () => {
      // Set up auth token
      localStorage.setItem("omoios_access_token", "mock-access-token")

      const { getCurrentUser } = await import("@/lib/api/auth")

      const user = await getCurrentUser()

      expect(user.email).toBe("test@example.com")
      expect(user.full_name).toBe("Test User")
      expect(user.is_verified).toBe(true)
    })

    it("fails when not authenticated", async () => {
      // Clear tokens
      localStorage.clear()

      server.use(
        http.get("*/api/v1/auth/me", () => {
          return HttpResponse.json(
            { detail: "Not authenticated" },
            { status: 401 }
          )
        })
      )

      const { getCurrentUser } = await import("@/lib/api/auth")

      await expect(getCurrentUser()).rejects.toThrow()
    })
  })
})

describe("API Error Handling", () => {
  it("handles 401 errors appropriately", async () => {
    server.use(
      http.get("*/api/v1/auth/me", () => {
        return HttpResponse.json(
          { detail: "Not authenticated" },
          { status: 401 }
        )
      })
    )

    const { getCurrentUser } = await import("@/lib/api/auth")

    await expect(getCurrentUser()).rejects.toThrow()
  })

  it("handles network errors", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () => {
        return HttpResponse.error()
      })
    )

    const { login } = await import("@/lib/api/auth")

    await expect(
      login({ email: "test@example.com", password: "password123" })
    ).rejects.toThrow()
  })

  it("handles validation errors", async () => {
    server.use(
      http.post("*/api/v1/auth/register", () => {
        return HttpResponse.json(
          {
            detail: [
              { loc: ["body", "email"], msg: "Invalid email format", type: "value_error" },
            ],
          },
          { status: 422 }
        )
      })
    )

    const { register } = await import("@/lib/api/auth")

    await expect(
      register({ email: "invalid", password: "password123" })
    ).rejects.toThrow()
  })
})
