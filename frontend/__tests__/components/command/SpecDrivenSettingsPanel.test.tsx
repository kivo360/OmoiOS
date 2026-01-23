import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SpecDrivenSettingsPanel } from "@/components/command/SpecDrivenSettingsPanel"
import * as useSpecDrivenSettingsModule from "@/hooks/useSpecDrivenSettings"
import type {
  SpecDrivenSettings,
  SpecDrivenSettingsUpdate,
} from "@/hooks/useSpecDrivenSettings"

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// Mock settings data
const mockSettings: SpecDrivenSettings = {
  id: "settings-1",
  user_id: "user-1",
  auto_execute: true,
  execution_mode: "auto",
  coverage_threshold: 80,
  enforce_coverage: true,
  parallel_execution: true,
  max_parallel_tasks: 3,
  validation_mode: "strict",
  require_tests: true,
  require_docs: false,
  auto_merge: false,
  notify_on_completion: true,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
}

// Create mock mutation functions
const mockMutateAsync = vi.fn()
const mockResetMutateAsync = vi.fn()

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

// Wrapper component with QueryClientProvider
function createWrapper() {
  const queryClient = createTestQueryClient()
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

describe("SpecDrivenSettingsPanel", () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("Loading State", () => {
    it("renders loading skeleton when data is loading", () => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isPending: true,
        isSuccess: false,
        status: "pending",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      expect(screen.getByTestId("settings-panel-loading")).toBeInTheDocument()
      expect(screen.getByText("Spec-Driven Settings")).toBeInTheDocument()
      expect(screen.getByText("Configure your spec-driven development workflow")).toBeInTheDocument()
    })
  })

  describe("Error State", () => {
    it("renders error alert when settings fail to load", () => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to load"),
        isError: true,
        isPending: false,
        isSuccess: false,
        status: "error",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      expect(screen.getByTestId("settings-panel-error")).toBeInTheDocument()
      expect(screen.getByText("Error")).toBeInTheDocument()
      expect(screen.getByText("Failed to load settings. Please try again.")).toBeInTheDocument()
    })
  })

  describe("Panel Display After Load", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)
    })

    it("displays all settings after successful load", () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      expect(screen.getByTestId("settings-panel")).toBeInTheDocument()
      expect(screen.getByText("Spec-Driven Settings")).toBeInTheDocument()

      // Check execution mode radio
      expect(screen.getByTestId("execution-mode-radio")).toBeInTheDocument()
      expect(screen.getByLabelText(/Automatic - Execute specs immediately/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Manual - Review specs before execution/)).toBeInTheDocument()

      // Check toggle switches
      expect(screen.getByTestId("auto-execute-switch")).toBeInTheDocument()
      expect(screen.getByTestId("enforce-coverage-switch")).toBeInTheDocument()
      expect(screen.getByTestId("parallel-execution-switch")).toBeInTheDocument()
      expect(screen.getByTestId("require-tests-switch")).toBeInTheDocument()
      expect(screen.getByTestId("require-docs-switch")).toBeInTheDocument()
      expect(screen.getByTestId("auto-merge-switch")).toBeInTheDocument()
      expect(screen.getByTestId("notify-completion-switch")).toBeInTheDocument()

      // Check slider
      expect(screen.getByTestId("coverage-slider")).toBeInTheDocument()
      expect(screen.getByTestId("coverage-value")).toHaveTextContent("80%")

      // Check validation mode radio
      expect(screen.getByTestId("validation-mode-radio")).toBeInTheDocument()

      // Check action buttons
      expect(screen.getByTestId("save-button")).toBeInTheDocument()
      expect(screen.getByTestId("reset-button")).toBeInTheDocument()
    })

    it("displays correct initial values from settings", () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      // Check that auto execution mode is selected
      const autoRadio = screen.getByLabelText(/Automatic - Execute specs immediately/)
      expect(autoRadio).toBeChecked()

      // Check switch states based on mock settings
      const autoExecuteSwitch = screen.getByTestId("auto-execute-switch")
      expect(autoExecuteSwitch).toHaveAttribute("data-state", "checked")

      const enforceCoverageSwitch = screen.getByTestId("enforce-coverage-switch")
      expect(enforceCoverageSwitch).toHaveAttribute("data-state", "checked")

      const autoMergeSwitch = screen.getByTestId("auto-merge-switch")
      expect(autoMergeSwitch).toHaveAttribute("data-state", "unchecked")

      // Check coverage value
      expect(screen.getByTestId("coverage-value")).toHaveTextContent("80%")
    })
  })

  describe("Toggle Switch Interactions", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)
    })

    it("toggles auto-execute switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const autoExecuteSwitch = screen.getByTestId("auto-execute-switch")
      expect(autoExecuteSwitch).toHaveAttribute("data-state", "checked")

      await user.click(autoExecuteSwitch)

      expect(autoExecuteSwitch).toHaveAttribute("data-state", "unchecked")
    })

    it("toggles parallel-execution switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const parallelSwitch = screen.getByTestId("parallel-execution-switch")
      expect(parallelSwitch).toHaveAttribute("data-state", "checked")

      await user.click(parallelSwitch)

      expect(parallelSwitch).toHaveAttribute("data-state", "unchecked")
    })

    it("toggles auto-merge switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const autoMergeSwitch = screen.getByTestId("auto-merge-switch")
      expect(autoMergeSwitch).toHaveAttribute("data-state", "unchecked")

      await user.click(autoMergeSwitch)

      expect(autoMergeSwitch).toHaveAttribute("data-state", "checked")
    })

    it("toggles require-tests switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const requireTestsSwitch = screen.getByTestId("require-tests-switch")
      expect(requireTestsSwitch).toHaveAttribute("data-state", "checked")

      await user.click(requireTestsSwitch)

      expect(requireTestsSwitch).toHaveAttribute("data-state", "unchecked")
    })

    it("toggles require-docs switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const requireDocsSwitch = screen.getByTestId("require-docs-switch")
      expect(requireDocsSwitch).toHaveAttribute("data-state", "unchecked")

      await user.click(requireDocsSwitch)

      expect(requireDocsSwitch).toHaveAttribute("data-state", "checked")
    })

    it("toggles notify-completion switch", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const notifySwitch = screen.getByTestId("notify-completion-switch")
      expect(notifySwitch).toHaveAttribute("data-state", "checked")

      await user.click(notifySwitch)

      expect(notifySwitch).toHaveAttribute("data-state", "unchecked")
    })
  })

  describe("Radio Group Selection", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)
    })

    it("changes execution mode from auto to manual", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const autoRadio = screen.getByLabelText(/Automatic - Execute specs immediately/)
      const manualRadio = screen.getByLabelText(/Manual - Review specs before execution/)

      expect(autoRadio).toBeChecked()
      expect(manualRadio).not.toBeChecked()

      await user.click(manualRadio)

      expect(autoRadio).not.toBeChecked()
      expect(manualRadio).toBeChecked()
    })

    it("changes validation mode", async () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const strictRadio = screen.getByLabelText(/Strict - All validations must pass/)
      const relaxedRadio = screen.getByLabelText(/Relaxed - Allow minor issues/)
      const noneRadio = screen.getByLabelText(/None - Skip validation/)

      expect(strictRadio).toBeChecked()

      await user.click(relaxedRadio)
      expect(relaxedRadio).toBeChecked()
      expect(strictRadio).not.toBeChecked()

      await user.click(noneRadio)
      expect(noneRadio).toBeChecked()
      expect(relaxedRadio).not.toBeChecked()
    })
  })

  describe("Slider Interactions", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)
    })

    it("displays coverage value from settings", () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      expect(screen.getByTestId("coverage-value")).toHaveTextContent("80%")
    })

    it("slider exists and is interactive", () => {
      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const slider = screen.getByTestId("coverage-slider")
      expect(slider).toBeInTheDocument()
    })
  })

  describe("Validation Errors", () => {
    it("shows validation error for invalid coverage threshold", async () => {
      // Create settings with invalid coverage
      const invalidSettings = { ...mockSettings, coverage_threshold: -10 }

      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: invalidSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      // Should show validation error
      expect(screen.getByTestId("coverage-error")).toBeInTheDocument()
      expect(screen.getByTestId("coverage-error")).toHaveTextContent("Coverage must be between 0 and 100")

      // Save button should be disabled
      expect(screen.getByTestId("save-button")).toBeDisabled()
    })
  })

  describe("Warning Banners", () => {
    it("shows warning when auto-merge is enabled with no validation", async () => {
      const riskySettings = {
        ...mockSettings,
        auto_merge: true,
        validation_mode: "none" as const,
      }

      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: riskySettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const warningsSection = screen.getByTestId("settings-warnings")
      expect(warningsSection).toBeInTheDocument()
      expect(screen.getByText(/Auto-merge with no validation is risky/)).toBeInTheDocument()
    })

    it("shows warning when auto-merge is enabled without required tests", async () => {
      const riskySettings = {
        ...mockSettings,
        auto_merge: true,
        require_tests: false,
      }

      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: riskySettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const warningsSection = screen.getByTestId("settings-warnings")
      expect(warningsSection).toBeInTheDocument()
      expect(screen.getByText(/Auto-merge without required tests could introduce bugs/)).toBeInTheDocument()
    })

    it("shows warning for low coverage threshold", async () => {
      const lowCoverageSettings = {
        ...mockSettings,
        coverage_threshold: 30,
        enforce_coverage: true,
      }

      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: lowCoverageSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const warningsSection = screen.getByTestId("settings-warnings")
      expect(warningsSection).toBeInTheDocument()
      expect(screen.getByText(/Coverage threshold below 50% may result in low-quality code/)).toBeInTheDocument()
    })
  })

  describe("Save Button", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)
    })

    it("calls mutation when save is clicked", async () => {
      mockMutateAsync.mockResolvedValueOnce(mockSettings)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const saveButton = screen.getByTestId("save-button")
      await user.click(saveButton)

      expect(mockMutateAsync).toHaveBeenCalled()
    })

    it("shows loading state during save", async () => {
      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const saveButton = screen.getByTestId("save-button")
      expect(saveButton).toBeDisabled()
    })

    it("is disabled when there are validation errors", async () => {
      const invalidSettings = { ...mockSettings, coverage_threshold: -10 }

      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: invalidSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const saveButton = screen.getByTestId("save-button")
      expect(saveButton).toBeDisabled()
    })
  })

  describe("Reset Button", () => {
    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)
    })

    it("calls reset mutation when clicked", async () => {
      mockResetMutateAsync.mockResolvedValueOnce({
        ...mockSettings,
        coverage_threshold: 80,
      })

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const resetButton = screen.getByTestId("reset-button")
      await user.click(resetButton)

      expect(mockResetMutateAsync).toHaveBeenCalled()
    })

    it("shows loading state during reset", async () => {
      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: true,
      } as any)

      render(<SpecDrivenSettingsPanel />, { wrapper: createWrapper() })

      const resetButton = screen.getByTestId("reset-button")
      expect(resetButton).toBeDisabled()
    })
  })

  describe("Unsaved Changes Dialog", () => {
    const mockOnClose = vi.fn()

    beforeEach(() => {
      vi.spyOn(useSpecDrivenSettingsModule, "useSpecDrivenSettings").mockReturnValue({
        data: mockSettings,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: "success",
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useUpdateSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as any)

      vi.spyOn(useSpecDrivenSettingsModule, "useResetSpecDrivenSettings").mockReturnValue({
        mutateAsync: mockResetMutateAsync,
        isPending: false,
      } as any)

      mockOnClose.mockClear()
    })

    it("does not show dialog when closing without changes", async () => {
      render(<SpecDrivenSettingsPanel onClose={mockOnClose} />, { wrapper: createWrapper() })

      const closeButton = screen.getByRole("button", { name: /close/i })
      await user.click(closeButton)

      // Should call onClose directly without dialog
      expect(mockOnClose).toHaveBeenCalled()
      expect(screen.queryByTestId("unsaved-changes-dialog")).not.toBeInTheDocument()
    })

    it("shows dialog when closing with unsaved changes", async () => {
      render(<SpecDrivenSettingsPanel onClose={mockOnClose} />, { wrapper: createWrapper() })

      // Make a change
      const autoExecuteSwitch = screen.getByTestId("auto-execute-switch")
      await user.click(autoExecuteSwitch)

      // Try to close
      const closeButton = screen.getByRole("button", { name: /close/i })
      await user.click(closeButton)

      // Dialog should appear
      expect(screen.getByTestId("unsaved-changes-dialog")).toBeInTheDocument()
      expect(screen.getByText("Unsaved Changes")).toBeInTheDocument()
      expect(screen.getByText(/You have unsaved changes/)).toBeInTheDocument()
    })

    it("keeps editing when clicking Keep Editing", async () => {
      render(<SpecDrivenSettingsPanel onClose={mockOnClose} />, { wrapper: createWrapper() })

      // Make a change
      const autoExecuteSwitch = screen.getByTestId("auto-execute-switch")
      await user.click(autoExecuteSwitch)

      // Try to close
      const closeButton = screen.getByRole("button", { name: /close/i })
      await user.click(closeButton)

      // Click Keep Editing
      const keepEditingButton = screen.getByRole("button", { name: /keep editing/i })
      await user.click(keepEditingButton)

      // Dialog should close, onClose should not be called
      await waitFor(() => {
        expect(screen.queryByTestId("unsaved-changes-dialog")).not.toBeInTheDocument()
      })
      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it("discards changes and closes when clicking Discard Changes", async () => {
      render(<SpecDrivenSettingsPanel onClose={mockOnClose} />, { wrapper: createWrapper() })

      // Make a change
      const autoExecuteSwitch = screen.getByTestId("auto-execute-switch")
      await user.click(autoExecuteSwitch)

      // Try to close
      const closeButton = screen.getByRole("button", { name: /close/i })
      await user.click(closeButton)

      // Click Discard Changes
      const discardButton = screen.getByRole("button", { name: /discard changes/i })
      await user.click(discardButton)

      // onClose should be called
      expect(mockOnClose).toHaveBeenCalled()
    })
  })
})

describe("getSettingsWarnings", () => {
  const { getSettingsWarnings } = useSpecDrivenSettingsModule

  it("returns warning for auto-merge with no validation", () => {
    const warnings = getSettingsWarnings({
      auto_merge: true,
      validation_mode: "none",
      require_tests: true, // explicitly set to avoid second warning
    })

    expect(warnings).toHaveLength(1)
    expect(warnings[0].field).toBe("auto_merge")
    expect(warnings[0].severity).toBe("warning")
  })

  it("returns warning for low coverage threshold", () => {
    const warnings = getSettingsWarnings({
      coverage_threshold: 30,
      enforce_coverage: true,
    })

    expect(warnings).toHaveLength(1)
    expect(warnings[0].field).toBe("coverage_threshold")
  })

  it("returns error for auto-merge without required tests", () => {
    const warnings = getSettingsWarnings({
      auto_merge: true,
      require_tests: false,
    })

    expect(warnings).toHaveLength(1)
    expect(warnings[0].severity).toBe("error")
  })

  it("returns multiple warnings for multiple issues", () => {
    const warnings = getSettingsWarnings({
      auto_merge: true,
      validation_mode: "none",
      require_tests: false,
    })

    expect(warnings.length).toBeGreaterThan(1)
  })

  it("returns empty array for safe configuration", () => {
    const warnings = getSettingsWarnings({
      auto_merge: false,
      validation_mode: "strict",
      coverage_threshold: 80,
    })

    expect(warnings).toHaveLength(0)
  })
})

describe("validateSettings", () => {
  const { validateSettings } = useSpecDrivenSettingsModule

  it("returns error for negative coverage threshold", () => {
    const errors = validateSettings({
      coverage_threshold: -10,
    })

    expect(errors).toHaveLength(1)
    expect(errors[0].field).toBe("coverage_threshold")
    expect(errors[0].message).toBe("Coverage must be between 0 and 100")
  })

  it("returns error for coverage threshold over 100", () => {
    const errors = validateSettings({
      coverage_threshold: 150,
    })

    expect(errors).toHaveLength(1)
    expect(errors[0].field).toBe("coverage_threshold")
  })

  it("returns error for max_parallel_tasks below 1", () => {
    const errors = validateSettings({
      max_parallel_tasks: 0,
    })

    expect(errors).toHaveLength(1)
    expect(errors[0].field).toBe("max_parallel_tasks")
    expect(errors[0].message).toBe("Parallel tasks must be between 1 and 10")
  })

  it("returns error for max_parallel_tasks over 10", () => {
    const errors = validateSettings({
      max_parallel_tasks: 15,
    })

    expect(errors).toHaveLength(1)
    expect(errors[0].field).toBe("max_parallel_tasks")
  })

  it("returns empty array for valid settings", () => {
    const errors = validateSettings({
      coverage_threshold: 80,
      max_parallel_tasks: 3,
    })

    expect(errors).toHaveLength(0)
  })

  it("returns multiple errors for multiple invalid fields", () => {
    const errors = validateSettings({
      coverage_threshold: -10,
      max_parallel_tasks: 15,
    })

    expect(errors).toHaveLength(2)
  })
})
