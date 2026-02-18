"use client";

import { cn } from "@/lib/utils";

interface LineChangesProps {
  additions: number;
  deletions: number;
  className?: string;
  showLabels?: boolean;
}

export function LineChanges({
  additions,
  deletions,
  className,
  showLabels = false,
}: LineChangesProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`;
    }
    return num.toString();
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-mono text-xs",
        className,
      )}
    >
      <span className="text-success">
        +{formatNumber(additions)}
        {showLabels && (
          <span className="ml-0.5 text-muted-foreground">added</span>
        )}
      </span>
      <span className="text-destructive">
        -{formatNumber(deletions)}
        {showLabels && (
          <span className="ml-0.5 text-muted-foreground">removed</span>
        )}
      </span>
    </span>
  );
}
