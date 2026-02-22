"use client";

import Link from "next/link";
import { Github, Twitter, Linkedin, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { OmoiOSLogo } from "@/components/ui/omoios-logo";

const footerLinks = {
  product: [
    { label: "Features", href: "#features" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Compare", href: "/compare" },
    { label: "Demo", href: "#demo" },
  ],
  openSource: [
    { label: "GitHub", href: "https://github.com/kivo360/OmoiOS" },
    { label: "OpenAlternative", href: "https://openalternative.co" },
    {
      label: "Changelog",
      href: "https://github.com/kivo360/OmoiOS/releases",
    },
  ],
};

const socialLinks = [
  {
    icon: Github,
    href: "https://github.com/kivo360/OmoiOS",
    label: "GitHub",
  },
  { icon: Twitter, href: "https://twitter.com/omoios", label: "Twitter" },
  {
    icon: Linkedin,
    href: "https://linkedin.com/company/omoios",
    label: "LinkedIn",
  },
  {
    icon: MessageCircle,
    href: "https://discord.gg/omoios",
    label: "Discord",
  },
];

interface FooterSectionProps {
  className?: string;
}

export function FooterSection({ className }: FooterSectionProps) {
  return (
    <footer
      className={cn("border-t border-gray-800 bg-landing-bg-dark", className)}
    >
      <div className="container mx-auto px-4 py-12 md:py-16">
        {/* Main Footer Content */}
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <Link href="/" className="inline-flex items-center gap-2">
              <OmoiOSLogo size="md" />
            </Link>
            <p className="mt-4 max-w-xs text-sm text-gray-400">
              Autonomous engineering execution. Turn feature requests into
              shipped code while you focus on what matters.
            </p>

            {/* Social Links */}
            <div className="mt-6 flex gap-4">
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-800 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
                  aria-label={social.label}
                >
                  <social.icon className="h-4 w-4" />
                </a>
              ))}
            </div>
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

          {/* Open Source Links */}
          <div>
            <h4 className="mb-4 text-sm font-semibold text-white">
              Open Source
            </h4>
            <ul className="space-y-3">
              {footerLinks.openSource.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-400 transition-colors hover:text-white"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-gray-800 pt-8 md:flex-row">
          <p className="text-sm text-gray-500">
            &copy; {new Date().getFullYear()} OmoiOS. All rights reserved.
          </p>
          <p className="text-sm text-gray-500">
            Open Source &middot; Apache 2.0
          </p>
        </div>
      </div>
    </footer>
  );
}
