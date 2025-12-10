/**
 * Static phase configuration
 * 
 * Phases are system-defined workflow stages. This configuration
 * defines the available phases and their properties.
 */

export interface PhaseConfig {
  id: string
  name: string
  description: string
  order: number
  isTerminal: boolean
  isSystem: boolean
  transitions: string[]
  doneCriteria: string[]
  expectedOutputs: { type: string; pattern: string; required: boolean }[]
  phasePrompt: string
  color: string
  config: {
    timeout: number
    maxRetries: number
    retryStrategy: string
    wipLimit: number
  }
}

export const PHASES: PhaseConfig[] = [
  {
    id: "PHASE_BACKLOG",
    name: "Backlog",
    description: "Initial collection point for new work items",
    order: 0,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_REQUIREMENTS", "PHASE_BLOCKED"],
    doneCriteria: [],
    expectedOutputs: [],
    phasePrompt: "",
    color: "#6B7280",
    config: { timeout: 0, maxRetries: 3, retryStrategy: "exponential", wipLimit: 0 },
  },
  {
    id: "PHASE_REQUIREMENTS",
    name: "Requirements Analysis",
    description: "Gathering and documenting detailed requirements",
    order: 1,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_DESIGN", "PHASE_BLOCKED"],
    doneCriteria: [
      "Requirements documented",
      "Acceptance criteria defined",
      "Scope confirmed",
    ],
    expectedOutputs: [
      { type: "file", pattern: "docs/requirements/*.md", required: true },
    ],
    phasePrompt: `Analyze and document requirements comprehensively.
Define clear acceptance criteria for each requirement.
Identify dependencies and constraints.
Flag any ambiguities for clarification.`,
    color: "#3B82F6",
    config: { timeout: 1800, maxRetries: 2, retryStrategy: "linear", wipLimit: 10 },
  },
  {
    id: "PHASE_DESIGN",
    name: "Design",
    description: "Architecture and solution design phase",
    order: 2,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_IMPLEMENTATION", "PHASE_BLOCKED"],
    doneCriteria: [
      "Design document created",
      "Architecture reviewed",
      "Technical approach approved",
    ],
    expectedOutputs: [
      { type: "file", pattern: "docs/design/*.md", required: true },
    ],
    phasePrompt: `Create detailed technical design.
Document architectural decisions and tradeoffs.
Identify potential risks and mitigations.
Define interfaces and data models.`,
    color: "#8B5CF6",
    config: { timeout: 3600, maxRetries: 2, retryStrategy: "linear", wipLimit: 5 },
  },
  {
    id: "PHASE_IMPLEMENTATION",
    name: "Implementation",
    description: "Developing and implementing features",
    order: 3,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_TESTING", "PHASE_BLOCKED"],
    doneCriteria: [
      "All code files created",
      "Minimum 3 test cases passing",
      "Code follows project style guidelines",
      "No critical linter errors",
    ],
    expectedOutputs: [
      { type: "file", pattern: "src/**/*.py", required: true },
      { type: "file", pattern: "tests/**/*.py", required: true },
      { type: "file", pattern: "docs/**/*.md", required: false },
    ],
    phasePrompt: `Focus on implementing core functionality first.
Write tests alongside code using TDD principles.
Follow existing code patterns and project conventions.
Document any significant architectural decisions.
If blocked, move to PHASE_BLOCKED with clear explanation.`,
    color: "#F59E0B",
    config: { timeout: 3600, maxRetries: 3, retryStrategy: "exponential", wipLimit: 5 },
  },
  {
    id: "PHASE_TESTING",
    name: "Testing",
    description: "Comprehensive testing and quality assurance",
    order: 4,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_DEPLOYMENT", "PHASE_IMPLEMENTATION", "PHASE_BLOCKED"],
    doneCriteria: [
      "All tests passing",
      "Code coverage above 80%",
      "No critical bugs",
    ],
    expectedOutputs: [
      { type: "file", pattern: "tests/**/*.py", required: true },
      { type: "report", pattern: "coverage.xml", required: true },
    ],
    phasePrompt: `Run comprehensive test suites.
Verify edge cases and error handling.
Check code coverage meets minimum requirements.
Document any known limitations.`,
    color: "#10B981",
    config: { timeout: 1800, maxRetries: 2, retryStrategy: "linear", wipLimit: 3 },
  },
  {
    id: "PHASE_DEPLOYMENT",
    name: "Deployment",
    description: "Release and deployment to production",
    order: 5,
    isTerminal: false,
    isSystem: true,
    transitions: ["PHASE_DONE"],
    doneCriteria: [
      "Deployment successful",
      "Health checks passing",
      "Monitoring configured",
    ],
    expectedOutputs: [],
    phasePrompt: `Execute deployment procedures carefully.
Verify all pre-deployment checks pass.
Monitor for any deployment issues.
Document deployment artifacts and versions.`,
    color: "#EC4899",
    config: { timeout: 1800, maxRetries: 1, retryStrategy: "none", wipLimit: 2 },
  },
  {
    id: "PHASE_DONE",
    name: "Done",
    description: "Completed and delivered work items",
    order: 6,
    isTerminal: true,
    isSystem: true,
    transitions: [],
    doneCriteria: [],
    expectedOutputs: [],
    phasePrompt: "",
    color: "#059669",
    config: { timeout: 0, maxRetries: 0, retryStrategy: "none", wipLimit: 0 },
  },
  {
    id: "PHASE_BLOCKED",
    name: "Blocked",
    description: "Items blocked by dependencies or issues",
    order: 99,
    isTerminal: false,
    isSystem: true,
    transitions: [
      "PHASE_BACKLOG",
      "PHASE_REQUIREMENTS",
      "PHASE_DESIGN",
      "PHASE_IMPLEMENTATION",
      "PHASE_TESTING",
    ],
    doneCriteria: [],
    expectedOutputs: [],
    phasePrompt: `Document blocking reason clearly.
Identify what is needed to unblock.
Set expected resolution timeline if possible.`,
    color: "#EF4444",
    config: { timeout: 0, maxRetries: 0, retryStrategy: "none", wipLimit: 0 },
  },
]

// Helper to get phase by ID
export function getPhaseById(phaseId: string): PhaseConfig | undefined {
  return PHASES.find((p) => p.id === phaseId)
}

// Get all phase IDs
export const ALL_PHASE_IDS = PHASES.map((p) => p.id)

// Get phases sorted by order
export function getPhasesSorted(): PhaseConfig[] {
  return [...PHASES].sort((a, b) => a.order - b.order)
}
