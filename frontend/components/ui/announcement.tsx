"use client";

import type { ComponentProps, HTMLAttributes } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type AnnouncementProps = ComponentProps<typeof Badge> & {
  themed?: boolean;
};

export const Announcement = ({
  variant = "outline",
  themed = false,
  className,
  ...props
}: AnnouncementProps) => (
  <Badge
    variant={variant}
    className={cn(
      "group gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-shadow hover:shadow-md",
      themed &&
        "border-landing-accent/30 bg-landing-accent/10 text-landing-accent hover:bg-landing-accent/20",
      className,
    )}
    {...props}
  />
);

export type AnnouncementTagProps = HTMLAttributes<HTMLSpanElement>;

export const AnnouncementTag = ({
  className,
  ...props
}: AnnouncementTagProps) => (
  <span
    className={cn(
      "rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground",
      "group-[.themed]:bg-landing-accent/20 group-[.themed]:text-landing-accent",
      className,
    )}
    {...props}
  />
);

export type AnnouncementTitleProps = HTMLAttributes<HTMLSpanElement>;

export const AnnouncementTitle = ({
  className,
  ...props
}: AnnouncementTitleProps) => (
  <span
    className={cn(
      "flex items-center gap-1 text-foreground",
      "group-[.themed]:text-landing-accent",
      className,
    )}
    {...props}
  />
);
