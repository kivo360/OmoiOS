import type { Metadata } from "next";
import { Check, X } from "lucide-react";
import { MarketingNavbar } from "@/components/marketing/FloatingNavbar";
import { FooterSection } from "@/components/marketing/sections/FooterSection";

export const metadata: Metadata = {
  title: "Compare OmoiOS vs Kiro vs Codex vs Claude Code",
  description:
    "See how OmoiOS compares to Kiro, OpenAI Codex, Claude Code, OpenCode, and Cursor. Open-source, spec-driven, autonomous agent orchestration.",
};

type CellValue = boolean | string;

interface ComparisonRow {
  label: string;
  omoios: CellValue;
  kiro: CellValue;
  codex: CellValue;
  claudeCode: CellValue;
  opencode: CellValue;
  cursor: CellValue;
}

const rows: ComparisonRow[] = [
  {
    label: "Open source",
    omoios: true,
    kiro: false,
    codex: false,
    claudeCode: true,
    opencode: "Yes (MIT)",
    cursor: false,
  },
  {
    label: "Where it runs",
    omoios: "Cloud (autonomous)",
    kiro: "Your IDE",
    codex: "Cloud + local CLI",
    claudeCode: "Your terminal",
    opencode: "Your terminal",
    cursor: "Your IDE",
  },
  {
    label: "You need to be",
    omoios: "Asleep",
    kiro: "At your desk",
    codex: "At your desk*",
    claudeCode: "At your desk",
    opencode: "At your desk",
    cursor: "At your desk",
  },
  {
    label: "Spec-to-code pipeline",
    omoios: "Full pipeline",
    kiro: "Specs + hooks",
    codex: "Prompt-driven",
    claudeCode: "Prompt-driven",
    opencode: "Prompt-driven",
    cursor: "Prompt-driven",
  },
  {
    label: "Multi-agent orchestration",
    omoios: "Parallel agents",
    kiro: "Single agent",
    codex: "Parallel tasks",
    claudeCode: "Subagents",
    opencode: "Multi-session",
    cursor: "Single agent",
  },
  {
    label: "Output",
    omoios: "PR ready to merge",
    kiro: "Code in editor",
    codex: "PR via GitHub",
    claudeCode: "Code changes locally",
    opencode: "Code changes locally",
    cursor: "Code in editor",
  },
  {
    label: "Self-healing execution",
    omoios: "Retries + auto-fix",
    kiro: "Manual",
    codex: "Runs tests to pass",
    claudeCode: "Manual",
    opencode: "Manual",
    cursor: "Manual",
  },
  {
    label: "Self-hostable",
    omoios: true,
    kiro: false,
    codex: false,
    claudeCode: false,
    opencode: "Local only",
    cursor: false,
  },
  {
    label: "BYOK (model provider)",
    omoios: "Anthropic, OpenAI",
    kiro: "Claude only",
    codex: "GPT only",
    claudeCode: "Claude only",
    opencode: "75+ providers",
    cursor: "Multiple",
  },
  {
    label: "Pricing",
    omoios: "Free–$150/mo",
    kiro: "Free (preview)",
    codex: "ChatGPT Plus+",
    claudeCode: "Pro/Max/API",
    opencode: "Free (BYOK)",
    cursor: "$20/mo+",
  },
];

const competitors = [
  { key: "omoios" as const, name: "OmoiOS", highlight: true },
  { key: "kiro" as const, name: "Kiro (AWS)", highlight: false },
  { key: "codex" as const, name: "OpenAI Codex", highlight: false },
  { key: "claudeCode" as const, name: "Claude Code", highlight: false },
  { key: "opencode" as const, name: "OpenCode (sst)", highlight: false },
  { key: "cursor" as const, name: "Cursor", highlight: false },
];

function CellContent({ value }: { value: CellValue }) {
  if (typeof value === "boolean") {
    return value ? (
      <Check className="mx-auto h-5 w-5 text-green-600" />
    ) : (
      <X className="mx-auto h-5 w-5 text-red-400" />
    );
  }
  return <span>{value}</span>;
}

const competitorSections = [
  {
    title: "How is OmoiOS different from Kiro?",
    body: "Kiro is a spec-driven IDE from AWS — it helps you plan and code interactively at your desk. OmoiOS is a spec-driven orchestration platform that runs autonomously in the cloud. You write the spec, approve the plan, and agents execute the full pipeline — delivering a PR while you focus on other work (or sleep). OmoiOS is also open-source and self-hostable, while Kiro is closed-source.",
  },
  {
    title: "How is OmoiOS different from OpenAI Codex?",
    body: "Codex is a cloud-based coding agent from OpenAI — you assign individual tasks via prompts, and it works in a sandbox to deliver code changes or PRs. OmoiOS is a spec-driven orchestration platform — you write a feature specification, agents generate requirements, design, and implementation plans, then execute the full pipeline autonomously. OmoiOS is also open-source, self-hostable, and supports multiple model providers (Anthropic + OpenAI), while Codex is closed-source, runs only on OpenAI's infrastructure, and uses GPT models exclusively.",
  },
  {
    title: "How is OmoiOS different from Claude Code?",
    body: "Claude Code is a powerful local coding agent that runs in your terminal alongside your IDE. It's excellent for interactive development — exploring codebases, debugging, and making changes with you in the loop. OmoiOS is designed for a different workflow: you define a spec, approve a plan, and agents execute the full pipeline in the cloud while you're away. Think of Claude Code as your pair programmer, and OmoiOS as your overnight engineering team.",
  },
  {
    title: "How is OmoiOS different from OpenCode?",
    body: "OpenCode (sst/opencode) is a great open-source CLI tool for interactive AI-assisted coding with support for 75+ model providers. Like Claude Code, it's a local tool that requires your presence. OmoiOS takes a different approach: cloud-based autonomous execution driven by specs, not prompts. Both are open source, but OmoiOS is infrastructure you deploy, not software you install.",
  },
  {
    title: "How is OmoiOS different from Cursor?",
    body: "Cursor is an AI-powered code editor that helps you write code faster with inline suggestions and chat. It's a productivity multiplier when you're at your desk. OmoiOS operates at a different layer — you're not writing code at all. You write a spec, agents plan and execute autonomously, and you review the PR when it's ready. Cursor makes you faster; OmoiOS works without you.",
  },
];

export default function ComparePage() {
  return (
    <div className="landing-page min-h-screen bg-landing-bg">
      <MarketingNavbar />

      <main className="px-4 pb-20 pt-28 md:pt-36">
        <div className="container mx-auto max-w-6xl">
          {/* Page Header */}
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-landing-text md:text-5xl">
              How OmoiOS compares
            </h1>
            <p className="mt-4 text-lg text-landing-text-muted">
              A side-by-side look at OmoiOS versus the leading AI coding tools.
            </p>
          </div>

          {/* Full Comparison Table */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] border-collapse text-sm">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 border-b border-landing-border bg-landing-bg p-3 text-left font-medium text-landing-text-muted" />
                  {competitors.map((comp) => (
                    <th
                      key={comp.key}
                      className={`border-b border-landing-border p-3 text-center font-semibold ${
                        comp.highlight
                          ? "bg-landing-accent/5 text-landing-accent"
                          : "text-landing-text"
                      }`}
                    >
                      {comp.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.label}>
                    <td className="sticky left-0 z-10 border-b border-landing-border bg-landing-bg p-3 font-medium text-landing-text">
                      {row.label}
                    </td>
                    {competitors.map((comp) => (
                      <td
                        key={comp.key}
                        className={`border-b border-landing-border p-3 text-center text-landing-text-muted ${
                          comp.highlight ? "bg-landing-accent/5" : ""
                        }`}
                      >
                        <CellContent value={row[comp.key]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-center text-xs italic text-landing-text-muted">
            * Codex cloud tasks run async, but still prompt-driven — no
            spec-to-code pipeline. You assign individual tasks, not a full
            feature spec.
          </p>

          {/* Per-Competitor Sections */}
          <div className="mx-auto mt-20 max-w-3xl space-y-16">
            {competitorSections.map((section) => (
              <div key={section.title}>
                <h2 className="text-2xl font-bold tracking-tight text-landing-text">
                  {section.title}
                </h2>
                <p className="mt-4 text-base leading-relaxed text-landing-text-muted">
                  {section.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <FooterSection />
    </div>
  );
}
