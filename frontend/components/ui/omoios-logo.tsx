"use client";

import { cn } from "@/lib/utils";

interface OmoiOSLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  textClassName?: string;
}

const sizeMap = {
  sm: { icon: "h-6 w-6", text: "text-sm" },
  md: { icon: "h-8 w-8", text: "text-base" },
  lg: { icon: "h-10 w-10", text: "text-lg" },
  xl: { icon: "h-12 w-12", text: "text-xl" },
};

export function OmoiOSLogo({
  className,
  size = "md",
  showText = true,
  textClassName,
}: OmoiOSLogoProps) {
  const { icon, text } = sizeMap[size];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <OmoiOSMark className={icon} />
      {showText && (
        <span
          className={cn(
            "font-semibold bg-gradient-to-r from-amber-200 via-yellow-400 to-orange-500 bg-clip-text text-transparent",
            text,
            textClassName,
          )}
        >
          OmoiOS
        </span>
      )}
    </div>
  );
}

interface OmoiOSMarkProps {
  className?: string;
}

export function OmoiOSMark({ className }: OmoiOSMarkProps) {
  return (
    <svg
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("h-8 w-8", className)}
      aria-label="OmoiOS"
    >
      <defs>
        <linearGradient
          id="omoios-gold-gradient"
          x1="120"
          y1="96"
          x2="392"
          y2="416"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#FFE78A" />
          <stop offset="0.35" stopColor="#FFD04A" />
          <stop offset="1" stopColor="#FF8A2A" />
        </linearGradient>
        <filter
          id="omoios-glow"
          x="-25%"
          y="-25%"
          width="150%"
          height="150%"
          colorInterpolationFilters="sRGB"
        >
          <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values="1 0 0 0 0
                    0 0.72 0 0 0
                    0 0 0.2 0 0
                    0 0 0 0.55 0"
            result="glowColor"
          />
          <feMerge>
            <feMergeNode in="glowColor" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g
        filter="url(#omoios-glow)"
        stroke="url(#omoios-gold-gradient)"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Core mark - 7 circles forming Flower of Life */}
        <g strokeWidth="14">
          <circle cx="256" cy="256" r="112" />
          <circle cx="368" cy="256" r="112" />
          <circle cx="312" cy="352.99" r="112" />
          <circle cx="200" cy="352.99" r="112" />
          <circle cx="144" cy="256" r="112" />
          <circle cx="200" cy="159.01" r="112" />
          <circle cx="312" cy="159.01" r="112" />
        </g>
        {/* Outer rings */}
        <g strokeWidth="10">
          <circle cx="256" cy="256" r="210" opacity="0.55" />
          <circle cx="256" cy="256" r="236" opacity="0.25" />
        </g>
      </g>
    </svg>
  );
}
