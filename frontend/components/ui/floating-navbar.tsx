"use client";
import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";
import { ArrowRight, Github } from "lucide-react";
import { OmoiOSLogo } from "@/components/ui/omoios-logo";

export const FloatingNav = ({
  navItems,
  className,
}: {
  navItems: {
    name: string;
    link: string;
    icon?: JSX.Element;
  }[];
  className?: string;
}) => {
  // Always visible - static navbar at top
  const [visible] = useState(true);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        initial={{
          opacity: 1,
          y: -100,
        }}
        animate={{
          y: visible ? 0 : -100,
          opacity: visible ? 1 : 0,
        }}
        transition={{
          duration: 0.2,
        }}
        className={cn(
          "fixed left-1/2 top-14 z-[5000] flex -translate-x-1/2 items-center justify-center space-x-4 rounded-full border border-landing-border bg-landing-bg/80 py-2 pl-8 pr-2 shadow-lg backdrop-blur-md",
          className,
        )}
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 pr-4">
          <OmoiOSLogo size="sm" textClassName="text-landing-text" />
        </Link>

        {/* Nav Items */}
        {navItems.map((navItem, idx: number) => (
          <a
            key={`link-${idx}`}
            href={navItem.link}
            className={cn(
              "relative flex items-center space-x-1 text-sm text-landing-text-muted transition-colors hover:text-landing-text",
            )}
          >
            <span className="block sm:hidden">{navItem.icon}</span>
            <span className="hidden sm:block">{navItem.name}</span>
          </a>
        ))}

        {/* GitHub Link */}
        <a
          href="https://github.com/kivo360/OmoiOS"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm text-landing-text-muted transition-colors hover:text-landing-text"
        >
          <Github className="h-4 w-4" />
          <span className="hidden lg:block">GitHub</span>
        </a>

        {/* CTA Button */}
        <Link
          href="/register"
          className="relative flex items-center gap-1 rounded-full bg-landing-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-landing-accent-dark"
        >
          <span>Get Started Free</span>
          <ArrowRight className="h-3 w-3" />
        </Link>
      </motion.div>
    </AnimatePresence>
  );
};
