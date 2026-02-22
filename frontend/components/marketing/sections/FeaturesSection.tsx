"use client";

import { motion } from "framer-motion";
import { Shield, RefreshCw, Eye, GitBranch } from "lucide-react";
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
import { cn } from "@/lib/utils";

const features = [
  {
    title: "Spec-driven guardrails",
    description:
      "Your spec is the contract. Agents can't go off-script. Requirements, constraints, and acceptance criteria are enforced at every step.",
    icon: Shield,
    className: "md:col-span-2",
    visual: <SpecDrivenVisual />,
  },
  {
    title: "Self-healing pipeline",
    description:
      "When tests fail or builds break, agents diagnose, fix, and retry automatically. You only hear about success.",
    icon: RefreshCw,
    className: "md:col-span-1",
    visual: <GuardianVisual />,
  },
  {
    title: "Full traceability",
    description:
      "Every decision, test result, and code change is linked back to the original requirement. Review with confidence because you can see why every line exists.",
    icon: Eye,
    className: "md:col-span-1",
    visual: <VisibilityVisual />,
  },
  {
    title: "Parallel orchestration",
    description:
      "Multiple agents, multiple tasks, dependency-aware sequencing. Scale throughput by adding agents — not meetings.",
    icon: GitBranch,
    className: "md:col-span-2",
    visual: <OrchestrationVisual />,
  },
];

interface FeaturesSectionProps {
  className?: string;
  id?: string;
}

export function FeaturesSection({ className, id }: FeaturesSectionProps) {
  return (
    <section
      id={id}
      className={cn("bg-landing-bg-warm py-20 md:py-32", className)}
    >
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Orchestrated execution, not prompt-and-pray
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Spec-driven guardrails, self-healing pipelines, and full
            traceability — so errors don&apos;t pile up.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <BentoGrid className="mx-auto max-w-5xl">
          {features.map((feature) => (
            <BentoGridItem
              key={feature.title}
              title={feature.title}
              description={feature.description}
              header={feature.visual}
              icon={<feature.icon className="h-4 w-4 text-landing-accent" />}
              className={cn(
                feature.className,
                "group border-landing-border bg-white hover:shadow-lg transition-all duration-300",
              )}
            />
          ))}
        </BentoGrid>
      </div>
    </section>
  );
}

// Visual Components for Bento Grid Items

function SpecDrivenVisual() {
  const phases = ["Requirements", "Design", "Plan", "Execution"];
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center gap-2 rounded-lg bg-landing-bg-muted p-4">
      {phases.map((phase, i) => (
        <motion.div
          key={phase}
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.1 }}
          className="flex items-center gap-2"
        >
          <div className="rounded-md bg-white px-3 py-2 text-xs font-medium text-landing-text shadow-sm">
            {phase}
          </div>
          {i < phases.length - 1 && (
            <div className="h-px w-4 bg-landing-accent" />
          )}
        </motion.div>
      ))}
    </div>
  );
}

function GuardianVisual() {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center rounded-lg bg-landing-bg-muted p-4">
      <motion.div
        animate={{ scale: [1, 1.1, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="relative"
      >
        <div className="h-16 w-16 rounded-full bg-landing-accent/10" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Shield className="h-6 w-6 text-landing-accent" />
        </div>
        <motion.div
          animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="absolute inset-0 rounded-full border-2 border-landing-accent"
        />
      </motion.div>
    </div>
  );
}

function VisibilityVisual() {
  return (
    <div className="flex h-full min-h-[120px] items-end gap-1 rounded-lg bg-landing-bg-muted p-4">
      {[40, 65, 45, 80, 55, 90, 70, 85, 60, 75].map((height, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          whileInView={{ height: `${height}%` }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.05, duration: 0.5 }}
          className="flex-1 rounded-t bg-landing-accent/60"
        />
      ))}
    </div>
  );
}

function OrchestrationVisual() {
  const agents = ["Agent 1", "Agent 2", "Agent 3"];
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center gap-4 rounded-lg bg-landing-bg-muted p-4">
      {agents.map((agent, i) => (
        <motion.div
          key={agent}
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.15 }}
          className="flex flex-col items-center gap-2"
        >
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-landing-accent/10"
          >
            <GitBranch className="h-5 w-5 text-landing-accent" />
          </motion.div>
          <span className="text-[10px] font-medium text-landing-text-muted">
            {agent}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
