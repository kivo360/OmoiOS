"use client"

import { ArrowUpRightIcon, X } from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export interface AnnouncementProps {
  tag?: string
  title: string
  href: string
  className?: string
  dismissible?: boolean
}

export function Announcement({
  tag,
  title,
  href,
  className,
  dismissible = true,
}: AnnouncementProps) {
  const [isVisible, setIsVisible] = useState(true)

  if (!isVisible) return null

  return (
    <div
      className={cn(
        "relative flex w-full items-center justify-center gap-2 bg-landing-accent px-4 py-2.5 text-sm text-white",
        className
      )}
    >
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 transition-opacity hover:opacity-90"
      >
        {tag && (
          <Badge
            variant="secondary"
            className="rounded-full bg-white/20 px-2 py-0.5 text-xs font-medium text-white hover:bg-white/30"
          >
            {tag}
          </Badge>
        )}
        <span className="font-medium">{title}</span>
        <ArrowUpRightIcon className="h-4 w-4 shrink-0" />
      </a>

      {dismissible && (
        <button
          onClick={() => setIsVisible(false)}
          className="absolute right-3 rounded-sm p-1 opacity-70 transition-opacity hover:opacity-100"
          aria-label="Dismiss announcement"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
