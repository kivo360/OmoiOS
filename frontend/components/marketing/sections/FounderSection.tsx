"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface FounderSectionProps {
  className?: string;
}

export function FounderSection({ className }: FounderSectionProps) {
  return (
    <section className={cn("bg-landing-bg-warm py-20 md:py-32", className)}>
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-2xl"
        >
          <h2 className="mb-8 text-center text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Built by a developer who got tired of babysitting AI
          </h2>

          <div className="space-y-5 text-base leading-relaxed text-landing-text-muted">
            <p>
              I&apos;m Kevin, a full-stack developer building OmoiOS as a solo
              founder. I&apos;ve shipped production code in Python, Rust,
              TypeScript, and Dart — and I&apos;ve used every AI coding tool out
              there.
            </p>

            <p>
              Here&apos;s what I kept running into: tools like Kiro and Cursor
              are great when you&apos;re at your desk. But I wanted something
              that could take a spec, execute a plan, and deliver a PR while I
              was asleep, at the gym, or working on something else entirely.
            </p>

            <p>
              So I built OmoiOS — an autonomous agent orchestration platform
              that treats specs as contracts and delivers tested code without
              requiring you at the keyboard.
            </p>

            <p>
              I open-sourced it because I think this should be infrastructure,
              not a walled garden. Fork it, self-host it, build on top of it.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
