"use client"

import { useState } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Menu, X, ArrowRight, Bot } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { name: "Why", link: "#why" },
  { name: "Features", link: "#features" },
  { name: "How It Works", link: "#how-it-works" },
  { name: "Pricing", link: "#consulting" },
]

interface OpenClawNavbarProps {
  className?: string
}

export function OpenClawNavbar({ className }: OpenClawNavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <>
      {/* Desktop Floating Nav */}
      <nav className={cn("fixed top-16 left-1/2 -translate-x-1/2 z-40 hidden md:flex", className)}>
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="flex items-center gap-2 rounded-full border border-landing-border bg-white/90 px-4 py-2 shadow-lg backdrop-blur-md"
        >
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 pr-4 border-r border-landing-border">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-landing-text">OpenClaw</span>
          </Link>

          {/* Nav Items */}
          <ul className="flex items-center gap-1">
            {navItems.map((item) => (
              <li key={item.name}>
                <Link
                  href={item.link}
                  className="whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium text-landing-text-muted transition-colors hover:bg-landing-bg-muted hover:text-landing-text"
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>

          {/* CTA */}
          <Link
            href="#consulting"
            className="ml-2 flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            Get Started Free
            <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </nav>

      {/* Mobile Header */}
      <header className="fixed left-0 right-0 top-11 z-50 md:hidden">
        <div className="mx-4 mt-4 flex items-center justify-between rounded-full border border-landing-border bg-white/80 px-4 py-2 backdrop-blur-md">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-landing-text">OpenClaw</span>
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
              className="mx-4 mt-2 overflow-hidden rounded-2xl border border-landing-border bg-white shadow-lg"
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

                <div className="mt-4 border-t border-landing-border pt-4">
                  <Link
                    href="#consulting"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white"
                  >
                    Get Started Free
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </header>
    </>
  )
}
