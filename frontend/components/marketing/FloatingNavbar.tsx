"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowRight, Github } from "lucide-react";
import { FloatingNav } from "@/components/ui/floating-navbar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { OmoiOSLogo } from "@/components/ui/omoios-logo";

const navItems = [
  { name: "Why", link: "#why" },
  { name: "Features", link: "#features" },
  { name: "How It Works", link: "#how-it-works" },
  { name: "Pricing", link: "#pricing" },
  { name: "Compare", link: "#compare" },
];

interface MarketingNavbarProps {
  className?: string;
}

export function MarketingNavbar({ className }: MarketingNavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Desktop Floating Nav */}
      <FloatingNav
        navItems={navItems}
        className={cn("hidden md:flex", className)}
      />

      {/* Mobile Header */}
      <header className="fixed left-0 right-0 top-11 z-50 md:hidden">
        <div className="mx-4 mt-4 flex items-center justify-between rounded-full border border-landing-border bg-landing-bg/80 px-4 py-2 backdrop-blur-md">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <OmoiOSLogo size="sm" textClassName="text-landing-text" />
          </Link>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-landing-text"
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mx-4 mt-2 overflow-hidden rounded-2xl border border-landing-border bg-landing-bg shadow-lg"
            >
              <nav className="p-4">
                <ul className="space-y-2">
                  {navItems.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.link}
                        onClick={() => setMobileMenuOpen(false)}
                        className="block rounded-lg px-4 py-3 text-landing-text transition-colors hover:bg-landing-bg-muted"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>

                <div className="mt-4 space-y-2 border-t border-landing-border pt-4">
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                    asChild
                  >
                    <a
                      href="https://github.com/kivo360/OmoiOS"
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <Github className="mr-2 h-4 w-4" />
                      GitHub
                    </a>
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                    asChild
                  >
                    <Link
                      href="/login"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Sign in
                    </Link>
                  </Button>
                  <Button
                    className="w-full bg-landing-accent hover:bg-landing-accent-dark"
                    asChild
                  >
                    <Link
                      href="/register"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Get Started Free
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </header>
    </>
  );
}
