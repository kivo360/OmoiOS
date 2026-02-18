"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Play,
  Loader2,
  Code,
  FileText,
  Github,
} from "lucide-react";
import { FlipWords } from "@/components/ui/flip-words";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const heroWords = [
  "shipped features",
  "merged PRs",
  "done work",
  "real results",
];

const heroVideos = [
  {
    id: "code-assistant",
    label: "Code Assistant",
    icon: Code,
    src: "/videos/code-assistant.mp4",
  },
  {
    id: "specs-driven",
    label: "Specs-Driven",
    icon: FileText,
    src: "/videos/specs-driven.mp4",
  },
];

interface HeroSectionProps {
  className?: string;
}

export function HeroSection({ className }: HeroSectionProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeVideo, setActiveVideo] = useState(0);
  const videoRefs = useRef<(HTMLVideoElement | null)[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    // Small delay for visual feedback before redirect
    setTimeout(() => {
      router.push(`/register?email=${encodeURIComponent(email)}`);
    }, 300);
  };

  useEffect(() => {
    // Play the active video, pause the other
    videoRefs.current.forEach((video, i) => {
      if (!video) return;
      if (i === activeVideo) {
        video.currentTime = 0;
        video.play().catch(() => {});
      } else {
        video.pause();
      }
    });
  }, [activeVideo]);

  return (
    <section
      className={cn(
        "relative overflow-hidden bg-landing-bg px-4 pb-16 pt-28 md:pb-24 md:pt-36",
        className,
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
              Now Available
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
              <FlipWords
                words={heroWords}
                duration={3000}
                className="text-landing-accent"
              />
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mx-auto mt-6 max-w-2xl text-lg text-landing-text-muted md:text-xl"
          >
            Describe what you want. We turn it into a plan with a clear schedule
            and traceable outputs—requirements, design, and tested code—until a
            pull request is ready for your review.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-10"
          >
            <form
              onSubmit={handleSubmit}
              className="mx-auto flex max-w-md gap-3"
            >
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
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Secondary CTAs */}
            <div className="mt-4 flex items-center justify-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                className="text-landing-text-muted"
                asChild
              >
                <Link href="#demo">
                  <Play className="mr-2 h-4 w-4" />
                  Watch Demo
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-landing-text-muted"
                asChild
              >
                <a
                  href="https://github.com/kivo360/OmoiOS"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Github className="mr-2 h-4 w-4" />
                  Star on GitHub
                </a>
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Video Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="relative mx-auto mt-16 max-w-5xl"
        >
          <div className="landing-shadow-lg overflow-hidden rounded-xl border border-landing-border bg-white">
            {/* Browser Chrome with Video Tabs */}
            <div className="flex items-center gap-2 border-b border-landing-border bg-landing-bg-muted px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
              </div>
              <div className="mx-auto flex gap-1 rounded-lg bg-white p-1">
                {heroVideos.map((video, index) => (
                  <button
                    key={video.id}
                    onClick={() => setActiveVideo(index)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all",
                      activeVideo === index
                        ? "bg-landing-accent text-white"
                        : "text-landing-text-muted hover:text-landing-text",
                    )}
                  >
                    <video.icon className="h-3 w-3" />
                    {video.label}
                  </button>
                ))}
              </div>
              <div className="w-[54px]" />{" "}
              {/* Spacer to balance traffic lights */}
            </div>

            {/* Video Player */}
            <div className="relative aspect-video bg-landing-bg-muted">
              {heroVideos.map((video, index) => (
                <video
                  key={video.id}
                  ref={(el) => {
                    videoRefs.current[index] = el;
                  }}
                  src={video.src}
                  muted
                  loop
                  playsInline
                  preload={index === 0 ? "auto" : "metadata"}
                  className={cn(
                    "absolute inset-0 h-full w-full object-cover object-top transition-opacity duration-300",
                    activeVideo === index ? "opacity-100" : "opacity-0",
                  )}
                />
              ))}
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
                <div className="text-xs font-medium text-landing-text">
                  Agent-Dev-1
                </div>
                <div className="text-[10px] text-green-600">
                  Building TASK-301
                </div>
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
                <svg
                  className="h-4 w-4 text-purple-600"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                >
                  <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-medium text-landing-text">
                  PR #147 Ready
                </div>
                <div className="text-[10px] text-landing-text-muted">
                  Add authentication
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
