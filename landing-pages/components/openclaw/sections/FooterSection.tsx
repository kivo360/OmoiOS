"use client"

import Link from "next/link"
import { Bot } from "lucide-react"
import { cn } from "@/lib/utils"

const footerLinks = {
  product: [
    { label: "Why OpenClaw", href: "#why" },
    { label: "Features", href: "#features" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Pricing", href: "#consulting" },
  ],
}

interface OpenClawFooterSectionProps {
  className?: string
}

export function OpenClawFooterSection({ className }: OpenClawFooterSectionProps) {
  return (
    <footer className={cn("border-t border-gray-800 bg-landing-bg-dark", className)}>
      <div className="container mx-auto px-4 py-12 md:py-16">
        {/* Main Footer Content */}
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <Link href="/" className="inline-flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-white">OpenClaw</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm text-gray-400">
              Stop babysitting ChatGPT. Deploy autonomous bots with proactive automation
              that work while you sleep.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="mb-4 text-sm font-semibold text-white">Product</h4>
            <ul className="space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-gray-400 transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-gray-800 pt-8 md:flex-row">
          <p className="text-sm text-gray-500">
            © {new Date().getFullYear()} OpenClaw. All rights reserved.
          </p>
          <p className="text-sm text-gray-500">
            Your AI assistant that never sleeps.
          </p>
        </div>
      </div>
    </footer>
  )
}
