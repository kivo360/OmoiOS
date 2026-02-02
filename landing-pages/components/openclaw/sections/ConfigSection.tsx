"use client"

import { motion } from "framer-motion"
import { Settings, Terminal, Shield, Lock, Globe, Database, Users, Cpu, Smartphone, Puzzle, Bot } from "lucide-react"
import { WobbleCard } from "@/components/ui/wobble-card"
import { NumberTicker } from "@/components/ui/number-ticker"
import Image from "next/image"

// Platform logos as simple colored circles with letters (could be replaced with actual SVG logos)
const PlatformLogo = ({ name, color }: { name: string; color: string }) => (
  <div
    className={`flex h-8 w-8 items-center justify-center rounded-full ${color} text-xs font-bold text-white shadow-sm`}
    title={name}
  >
    {name[0]}
  </div>
)

const configs = [
  {
    icon: Users,
    category: "Multi-Agent Configuration",
    description: "Run multiple isolated agents with separate workspaces, tools, and model overrides.",
    badge: "Run 3+ Agents",
    color: "bg-purple-500",
    badgeColor: "bg-purple-100 text-purple-700",
    stat: { value: 3, suffix: "+", label: "Concurrent Agents" },
    size: "large", // Takes 2 columns
  },
  {
    icon: Globe,
    category: "Channel Configuration",
    description: "Per-channel settings for WhatsApp, Telegram, Discord, Slack, and more.",
    badge: "10+ Platforms",
    color: "bg-blue-500",
    badgeColor: "bg-blue-100 text-blue-700",
    platforms: [
      { name: "WhatsApp", color: "bg-green-500" },
      { name: "Telegram", color: "bg-sky-500" },
      { name: "Discord", color: "bg-indigo-500" },
      { name: "Slack", color: "bg-purple-600" },
      { name: "Signal", color: "bg-blue-600" },
    ],
    size: "normal",
  },
  {
    icon: Lock,
    category: "Security & Access",
    description: "DM pair codes, allowlists, group restrictions, and sandbox isolation.",
    badge: "Enterprise Security",
    color: "bg-red-500",
    badgeColor: "bg-red-100 text-red-700",
    features: ["Pair Codes", "Allowlists", "Sandbox"],
    size: "normal",
  },
  {
    icon: Puzzle,
    category: "Skills & Automation",
    description: "Community skills from ClawHub, custom skills, webhooks, and Gmail integration.",
    badge: "50+ Skills",
    color: "bg-emerald-500",
    badgeColor: "bg-emerald-100 text-emerald-700",
    stat: { value: 50, suffix: "+", label: "Pre-built Skills" },
    size: "normal",
  },
  {
    icon: Cpu,
    category: "Model Configuration",
    description: "Anthropic Claude, OpenAI GPT-4, custom providers with failover support.",
    badge: "Multi-Provider",
    color: "bg-amber-500",
    badgeColor: "bg-amber-100 text-amber-700",
    models: ["Claude", "GPT-4", "Custom"],
    size: "normal",
  },
  {
    icon: Smartphone,
    category: "Companion Apps",
    description: "macOS, iOS, and Android apps with Voice Wake, Talk Mode, Canvas UI.",
    badge: "Cross-Platform",
    color: "bg-pink-500",
    badgeColor: "bg-pink-100 text-pink-700",
    platforms: [
      { name: "macOS", color: "bg-gray-700" },
      { name: "iOS", color: "bg-gray-900" },
      { name: "Android", color: "bg-green-600" },
    ],
    size: "large", // Takes 2 columns
  },
]

export function OpenClawConfigSection() {
  return (
    <section className="bg-landing-bg-muted py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <div className="mb-6 inline-flex items-center justify-center rounded-full border border-landing-border bg-white px-4 py-2">
            <Settings className="mr-2 h-5 w-5 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              Fully Customizable
            </span>
          </div>

          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Tweak Everything. Or Nothing.
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            Works out of the box. But if you're a control freak (we get it),
            you can customize agents, channels, security, models — everything.
          </p>
        </motion.div>

        {/* Bento Grid Layout */}
        <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2 lg:grid-cols-3">
          {configs.map((config, index) => (
            <motion.div
              key={config.category}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.08, duration: 0.5 }}
              className={config.size === "large" ? "md:col-span-2 lg:col-span-2" : ""}
            >
              <WobbleCard
                containerClassName={`h-full bg-white border border-landing-border ${config.size === "large" ? "min-h-[200px]" : "min-h-[240px]"}`}
                className="p-6"
              >
                <div className="relative z-10 flex h-full flex-col">
                  {/* Header */}
                  <div className="mb-4 flex items-start justify-between">
                    <div className={`inline-flex items-center justify-center rounded-xl ${config.color} p-3 text-white shadow-lg`}>
                      <config.icon className="h-5 w-5" />
                    </div>
                    <span className={`rounded-full ${config.badgeColor} px-3 py-1 text-xs font-semibold`}>
                      {config.badge}
                    </span>
                  </div>

                  {/* Content */}
                  <h3 className="mb-2 text-lg font-bold text-landing-text">{config.category}</h3>
                  <p className="mb-4 flex-1 text-sm text-landing-text-muted">{config.description}</p>

                  {/* Visual Element - varies by card type */}
                  <div className="mt-auto">
                    {/* Stats with animated number */}
                    {config.stat && (
                      <div className="flex items-center gap-3 rounded-xl bg-landing-bg-muted p-3">
                        <div className="flex items-baseline">
                          <NumberTicker
                            value={config.stat.value}
                            delay={0.3 + index * 0.1}
                            className="text-2xl font-bold text-landing-text"
                          />
                          <span className="text-xl font-bold text-landing-accent">{config.stat.suffix}</span>
                        </div>
                        <span className="text-sm text-landing-text-muted">{config.stat.label}</span>
                      </div>
                    )}

                    {/* Platform logos */}
                    {config.platforms && (
                      <div className="flex items-center gap-2">
                        <div className="flex -space-x-2">
                          {config.platforms.map((platform) => (
                            <PlatformLogo key={platform.name} name={platform.name} color={platform.color} />
                          ))}
                        </div>
                        <span className="text-sm text-landing-text-muted">
                          {config.platforms.length === 5 ? "& 5+ more" : ""}
                        </span>
                      </div>
                    )}

                    {/* Feature pills */}
                    {config.features && (
                      <div className="flex flex-wrap gap-2">
                        {config.features.map((feature) => (
                          <span
                            key={feature}
                            className="rounded-full bg-landing-bg-muted px-3 py-1 text-xs font-medium text-landing-text"
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Model pills */}
                    {config.models && (
                      <div className="flex flex-wrap gap-2">
                        {config.models.map((model, i) => (
                          <span
                            key={model}
                            className={`rounded-full px-3 py-1 text-xs font-medium ${
                              i === 0
                                ? "bg-amber-100 text-amber-700"
                                : i === 1
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </WobbleCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
