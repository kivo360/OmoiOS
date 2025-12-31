"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowRight, Play, Loader2 } from "lucide-react"
import { FlipWords } from "@/components/ui/flip-words"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

const heroWords = ["shipped features", "merged PRs", "done work", "real results"]

const avatars = [
  { src: "https://api.dicebear.com/7.x/avataaars/svg?seed=james", fallback: "JD" },
  { src: "https://api.dicebear.com/7.x/avataaars/svg?seed=sarah", fallback: "SK" },
  { src: "https://api.dicebear.com/7.x/avataaars/svg?seed=mike", fallback: "MP" },
  { src: "https://api.dicebear.com/7.x/avataaars/svg?seed=alex", fallback: "AL" },
  { src: "https://api.dicebear.com/7.x/avataaars/svg?seed=rachel", fallback: "RK" },
]

interface HeroSectionProps {
  className?: string
}

export function HeroSection({ className }: HeroSectionProps) {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsSubmitting(true)
    // Small delay for visual feedback before redirect
    setTimeout(() => {
      router.push(`/register?email=${encodeURIComponent(email)}&source=waitlist`)
    }, 300)
  }

  return (
    <section
      className={cn(
        "relative overflow-hidden bg-landing-bg px-4 pb-20 pt-32 md:pb-32 md:pt-40",
        className
      )}
    >
      {/* Subtle background gradient - non-animated */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-1/4 top-0 h-[300px] w-[300px] rounded-full bg-landing-accent/[0.03] blur-3xl" />
        <div className="absolute -right-1/4 bottom-0 h-[250px] w-[250px] rounded-full bg-landing-accent/[0.03] blur-3xl" />
      </div>

      <div className="container relative mx-auto max-w-5xl">
        {/* Main Content */}
        <div className="mx-auto max-w-3xl text-center">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <span className="inline-flex items-center gap-2 rounded-full bg-landing-accent/10 px-4 py-1.5 text-sm font-medium text-landing-accent">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-landing-accent opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-landing-accent" />
              </span>
              Now in Early Access
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl font-bold tracking-tight text-landing-text sm:text-5xl md:text-6xl lg:text-7xl"
          >
            Describe it. Wake up to{" "}
            <span className="text-landing-accent">
              <FlipWords words={heroWords} duration={3000} className="text-landing-accent" />
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mx-auto mt-6 max-w-2xl text-lg text-landing-text-muted md:text-xl"
          >
            Tell us what you want built in plain English. By morning, there&apos;s a
            pull request waiting for your review. That&apos;s it.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-10"
          >
            <form onSubmit={handleSubmit} className="mx-auto flex max-w-md gap-3">
              <Input
                type="email"
                placeholder="Enter your work email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 flex-1 border-landing-border bg-white text-landing-text placeholder:text-landing-text-subtle"
                required
                disabled={isSubmitting}
              />
              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting}
                className="h-12 bg-landing-accent px-6 text-white hover:bg-landing-accent-dark"
              >
                {isSubmitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    Join Waitlist
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Secondary CTA */}
            <div className="mt-4 flex items-center justify-center gap-4">
              <Button variant="ghost" size="sm" className="text-landing-text-muted" asChild>
                <Link href="#demo">
                  <Play className="mr-2 h-4 w-4" />
                  Watch Demo
                </Link>
              </Button>
            </div>
          </motion.div>

          {/* Social Proof */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
          >
            {/* Avatar Stack */}
            <div className="flex -space-x-3">
              {avatars.map((avatar, i) => (
                <Avatar
                  key={i}
                  className="h-10 w-10 border-2 border-white ring-0"
                >
                  <AvatarImage src={avatar.src} />
                  <AvatarFallback className="bg-landing-bg-muted text-xs text-landing-text-muted">
                    {avatar.fallback}
                  </AvatarFallback>
                </Avatar>
              ))}
            </div>

            {/* Stars & Count */}
            <div className="flex items-center gap-2">
              <div className="flex text-yellow-400">
                {[...Array(5)].map((_, i) => (
                  <svg
                    key={i}
                    className="h-4 w-4 fill-current"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <span className="text-sm text-landing-text-muted">
                <span className="font-semibold text-landing-text">500+</span> engineers on the waitlist
              </span>
            </div>
          </motion.div>
        </div>

        {/* Dashboard Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="relative mx-auto mt-16 max-w-5xl"
        >
          <div className="landing-shadow-lg overflow-hidden rounded-xl border border-landing-border bg-white">
            {/* Browser Chrome */}
            <div className="flex items-center gap-2 border-b border-landing-border bg-landing-bg-muted px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
              </div>
              <div className="mx-auto rounded-md bg-white px-4 py-1 text-xs text-landing-text-subtle">
                app.omoios.dev/board/acme-corp
              </div>
            </div>

            {/* Real Kanban Board Screenshot */}
            <div className="relative aspect-[16/9] bg-landing-bg-muted">
              <Image
                src="/screenshots/agent-task-view.png"
                alt="OmoiOS Kanban Board showing tasks in Backlog, Analyzing, Building, Testing, and Done columns"
                fill
                className="object-cover object-top"
                priority
              />
            </div>
          </div>

          {/* Floating Agent Status */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
            className="absolute -right-4 top-1/3 rounded-lg border border-landing-border bg-white p-3 shadow-lg md:-right-8"
          >
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="h-8 w-8 rounded-full bg-landing-accent/10" />
                <div className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-white bg-green-500" />
              </div>
              <div>
                <div className="text-xs font-medium text-landing-text">Agent-Dev-1</div>
                <div className="text-[10px] text-green-600">Building TASK-301</div>
              </div>
            </div>
          </motion.div>

          {/* Floating PR Preview */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 1 }}
            className="absolute -left-4 bottom-1/4 rounded-lg border border-landing-border bg-white p-3 shadow-lg md:-left-8"
          >
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-purple-100">
                <svg className="h-4 w-4 text-purple-600" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-medium text-landing-text">PR #147 Ready</div>
                <div className="text-[10px] text-landing-text-muted">Add authentication</div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
