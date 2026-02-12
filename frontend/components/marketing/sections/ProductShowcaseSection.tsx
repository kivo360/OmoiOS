"use client"

import { useState } from "react"
import Image from "next/image"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard,
  FolderKanban,
  Terminal,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const showcaseItems = [
  {
    id: "command",
    title: "Command Center",
    description: "Describe what you want to build in plain English. Select your repo, branch, and model. Launch an agent with one click.",
    icon: MessageSquare,
    image: "/screenshots/kanban-board.png",
    alt: "OmoiOS Command Center - describe what you want to build",
  },
  {
    id: "kanban",
    title: "Kanban Board",
    description: "Watch work flow through the pipeline: Backlog → Analyzing → Building → Testing → Deploying → Done. Full visibility into agent progress.",
    icon: FolderKanban,
    image: "/screenshots/agent-task-view.png",
    alt: "OmoiOS Kanban Board showing task pipeline",
  },
  {
    id: "project",
    title: "Project Dashboard",
    description: "One view for everything: active work, running agents, commit history, and GitHub integration. Know exactly where every project stands.",
    icon: LayoutDashboard,
    image: "/screenshots/command-center.png",
    alt: "OmoiOS Project Dashboard with overview stats",
  },
  {
    id: "agent",
    title: "Live Agent View",
    description: "Watch agents work in real-time: see the code they write, commands they run, and decisions they make. Full transparency, zero babysitting.",
    icon: Terminal,
    image: "/screenshots/project-overview.png",
    alt: "OmoiOS Live Agent View showing real-time code execution",
  },
]

interface ProductShowcaseSectionProps {
  className?: string
  id?: string
}

export function ProductShowcaseSection({ className, id }: ProductShowcaseSectionProps) {
  const [activeIndex, setActiveIndex] = useState(0)
  const activeItem = showcaseItems[activeIndex]

  const handlePrev = () => {
    setActiveIndex((prev) => (prev === 0 ? showcaseItems.length - 1 : prev - 1))
  }

  const handleNext = () => {
    setActiveIndex((prev) => (prev === showcaseItems.length - 1 ? 0 : prev + 1))
  }

  return (
    <section id={id} className={cn("bg-landing-bg py-20 md:py-32", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            See the Product in Action
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Real screenshots from real projects. No mockups, no Figma dreams.
          </p>
        </motion.div>

        {/* Tab Navigation */}
        <div className="mx-auto mb-8 max-w-3xl">
          <div className="flex flex-wrap justify-center gap-2">
            {showcaseItems.map((item, index) => (
              <button
                key={item.id}
                onClick={() => setActiveIndex(index)}
                className={cn(
                  "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all",
                  activeIndex === index
                    ? "bg-landing-accent text-white"
                    : "bg-landing-bg-muted text-landing-text-muted hover:bg-landing-bg-muted/80"
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.title}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Screenshot Display */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-6xl"
        >
          <div className="relative">
            {/* Browser Frame */}
            <div className="overflow-hidden rounded-xl border border-landing-border bg-white shadow-2xl">
              {/* Browser Chrome */}
              <div className="flex items-center justify-between border-b border-landing-border bg-landing-bg-muted px-4 py-3">
                <div className="flex gap-1.5">
                  <div className="h-3 w-3 rounded-full bg-red-400" />
                  <div className="h-3 w-3 rounded-full bg-yellow-400" />
                  <div className="h-3 w-3 rounded-full bg-green-400" />
                </div>
                <div className="rounded-md bg-white px-4 py-1 text-xs text-landing-text-subtle">
                  app.omoios.dev
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handlePrev}
                    className="h-6 w-6 p-0 text-landing-text-muted hover:text-landing-text"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleNext}
                    className="h-6 w-6 p-0 text-landing-text-muted hover:text-landing-text"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Screenshot */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeItem.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                  className="relative aspect-video"
                >
                  <Image
                    src={activeItem.image}
                    alt={activeItem.alt}
                    fill
                    className="object-cover object-top"
                    priority={activeIndex === 0}
                  />
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Description Card */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeItem.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="mt-6 text-center"
              >
                <h3 className="text-xl font-semibold text-landing-text">
                  {activeItem.title}
                </h3>
                <p className="mx-auto mt-2 max-w-xl text-landing-text-muted">
                  {activeItem.description}
                </p>
              </motion.div>
            </AnimatePresence>

            {/* Pagination Dots */}
            <div className="mt-6 flex justify-center gap-2">
              {showcaseItems.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setActiveIndex(index)}
                  className={cn(
                    "h-2 rounded-full transition-all",
                    activeIndex === index
                      ? "w-6 bg-landing-accent"
                      : "w-2 bg-landing-border hover:bg-landing-text-muted"
                  )}
                />
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
