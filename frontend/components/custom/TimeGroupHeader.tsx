"use client";

import { cn } from "@/lib/utils";

interface TimeGroupHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function TimeGroupHeader({ children, className }: TimeGroupHeaderProps) {
  return (
    <h3
      className={cn(
        "px-2 py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground",
        className,
      )}
    >
      {children}
    </h3>
  );
}
