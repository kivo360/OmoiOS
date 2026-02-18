"use client";

import { motion } from "framer-motion";
import {
  Bot,
  Zap,
  Shield,
  GitBranch,
  RefreshCw,
  Eye,
  Lightbulb,
  CheckCircle2,
} from "lucide-react";
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
import { cn } from "@/lib/utils";

const features = [
  {
    title: "You Stay in Control",
    description:
      "Review and approve before code is written. You make the decisions—we do the work.",
    icon: Zap,
    className: "md:col-span-2",
    visual: <SpecDrivenVisual />,
  },
  {
    title: "Work Doesn’t Get Stuck",
    description:
      "If something goes wrong, it retries and self-corrects. No babysitting required.",
    icon: Shield,
    className: "md:col-span-1",
    visual: <GuardianVisual />,
  },
  {
    title: "Handles the Unexpected",
    description:
      "Discovers edge cases and missing requirements as it works. You'll be asked only when it matters.",
    icon: Lightbulb,
    className: "md:col-span-1",
    visual: <DiscoveryVisual />,
  },
  {
    title: "Built-In Quality Checks",
    description:
      "Every piece of code is tested before you see it. Problems are caught and fixed automatically.",
    icon: CheckCircle2,
    className: "md:col-span-1",
    visual: <VerificationVisual />,
  },
  {
    title: "Mistakes Get Fixed, Not Escalated",
    description:
      "When something breaks, it retries and self-corrects. You only hear about it when it's done.",
    icon: RefreshCw,
    className: "md:col-span-1",
    visual: <SelfHealingVisual />,
  },
  {
    title: "See Everything, Stress About Nothing",
    description:
      "Full visibility into what's happening. Check in when you want, not because you have to.",
    icon: Eye,
    className: "md:col-span-2",
    visual: <VisibilityVisual />,
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
            An Army of Agents. In Formation.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Orchestrated execution with guardrails, tests, and
            self-correction—so errors don&apos;t pile up.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <BentoGrid className="mx-auto max-w-5xl">
          {features.map((feature, i) => (
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

function DiscoveryVisual() {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center rounded-lg bg-landing-bg-muted p-4">
      <div className="relative">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
          className="h-16 w-16"
        >
          {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
            <motion.div
              key={angle}
              className="absolute h-2 w-2 rounded-full bg-landing-accent"
              style={{
                left: "50%",
                top: "50%",
                transform: `rotate(${angle}deg) translateX(24px) translateY(-50%)`,
              }}
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: angle / 360,
              }}
            />
          ))}
        </motion.div>
        <Lightbulb className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 text-landing-accent" />
      </div>
    </div>
  );
}

function VerificationVisual() {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center gap-3 rounded-lg bg-landing-bg-muted p-4">
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, scale: 0 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.2 }}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100"
        >
          <CheckCircle2 className="h-5 w-5 text-green-600" />
        </motion.div>
      ))}
    </div>
  );
}

function SelfHealingVisual() {
  return (
    <div className="flex h-full min-h-[120px] items-center justify-center rounded-lg bg-landing-bg-muted p-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
      >
        <RefreshCw className="h-10 w-10 text-landing-accent" />
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
