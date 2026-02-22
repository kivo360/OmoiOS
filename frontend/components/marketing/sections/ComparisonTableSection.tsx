"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

type CellValue = boolean | string;

interface ComparisonRow {
  label: string;
  omoios: CellValue;
  kiro: CellValue;
  codex: CellValue;
  claudeCode: CellValue;
}

const rows: ComparisonRow[] = [
  {
    label: "Open source",
    omoios: true,
    kiro: false,
    codex: false,
    claudeCode: true,
  },
  {
    label: "Where it runs",
    omoios: "Cloud (autonomous)",
    kiro: "Your IDE",
    codex: "Cloud + local",
    claudeCode: "Your terminal",
  },
  {
    label: "Spec-to-code pipeline",
    omoios: "Full pipeline",
    kiro: "Specs + hooks",
    codex: "Prompt-driven",
    claudeCode: "Prompt-driven",
  },
  {
    label: "Multi-agent orchestration",
    omoios: "Parallel agents",
    kiro: "Single agent",
    codex: "Parallel tasks",
    claudeCode: "Subagents",
  },
  {
    label: "Self-hostable",
    omoios: true,
    kiro: false,
    codex: false,
    claudeCode: false,
  },
  {
    label: "BYOK (model provider)",
    omoios: "Anthropic, OpenAI",
    kiro: "Claude only",
    codex: "GPT only",
    claudeCode: "Claude only",
  },
];

const competitors = [
  { key: "omoios" as const, name: "OmoiOS", highlight: true },
  { key: "kiro" as const, name: "Kiro (AWS)", highlight: false },
  { key: "codex" as const, name: "OpenAI Codex", highlight: false },
  { key: "claudeCode" as const, name: "Claude Code", highlight: false },
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

interface ComparisonTableSectionProps {
  className?: string;
  id?: string;
}

export function ComparisonTableSection({
  className,
  id,
}: ComparisonTableSectionProps) {
  return (
    <section id={id} className={cn("bg-landing-bg py-20 md:py-32", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            How OmoiOS compares
          </h2>
        </motion.div>

        {/* Comparison Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="mx-auto max-w-4xl overflow-x-auto"
        >
          <table className="w-full min-w-[600px] border-collapse text-sm">
            <thead>
              <tr>
                <th className="border-b border-landing-border p-3 text-left font-medium text-landing-text-muted" />
                {competitors.map((comp) => (
                  <th
                    key={comp.key}
                    className={cn(
                      "border-b border-landing-border p-3 text-center font-semibold",
                      comp.highlight
                        ? "bg-landing-accent/5 text-landing-accent"
                        : "text-landing-text",
                    )}
                  >
                    {comp.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label}>
                  <td className="border-b border-landing-border p-3 font-medium text-landing-text">
                    {row.label}
                  </td>
                  {competitors.map((comp) => (
                    <td
                      key={comp.key}
                      className={cn(
                        "border-b border-landing-border p-3 text-center text-landing-text-muted",
                        comp.highlight && "bg-landing-accent/5",
                      )}
                    >
                      <CellContent value={row[comp.key]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        {/* Subheader */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="mx-auto mt-8 max-w-2xl text-center text-base italic text-landing-text-muted"
        >
          Kiro plans your code. Codex runs tasks. OmoiOS ships features — from
          spec to PR, overnight.
        </motion.p>
      </div>
    </section>
  );
}
