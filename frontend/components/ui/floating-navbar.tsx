"use client";
import React, { useState } from "react";
import Link from "next/link";
import {
  motion,
  AnimatePresence,
} from "motion/react";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

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
          "fixed inset-x-0 top-6 z-[5000] mx-auto flex max-w-fit items-center justify-center space-x-4 rounded-full border border-landing-border bg-white/80 py-2 pl-8 pr-2 shadow-lg backdrop-blur-md",
          className
        )}
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 pr-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-landing-accent">
            <span className="text-xs font-bold text-white">O</span>
          </div>
          <span className="font-semibold text-landing-text">OmoiOS</span>
        </Link>

        {/* Nav Items */}
        {navItems.map((navItem, idx: number) => (
          <a
            key={`link-${idx}`}
            href={navItem.link}
            className={cn(
              "relative flex items-center space-x-1 text-sm text-landing-text-muted transition-colors hover:text-landing-text"
            )}
          >
            <span className="block sm:hidden">{navItem.icon}</span>
            <span className="hidden sm:block">{navItem.name}</span>
          </a>
        ))}

        {/* CTA Button */}
        <Link
          href="/register"
          className="relative flex items-center gap-1 rounded-full bg-landing-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-landing-accent-dark"
        >
          <span>Get Early Access</span>
          <ArrowRight className="h-3 w-3" />
        </Link>
      </motion.div>
    </AnimatePresence>
  );
};
