// Animation utilities for landing page components
import { Variants } from "framer-motion"

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
}

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
}

export const staggerContainer: Variants = {
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
}

export const scaleIn: Variants = {
  initial: { scale: 0, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
}

export const slideInFromLeft: Variants = {
  initial: { x: -50, opacity: 0 },
  animate: { x: 0, opacity: 1 },
}

export const slideInFromRight: Variants = {
  initial: { x: 50, opacity: 0 },
  animate: { x: 0, opacity: 1 },
}

// For typewriter effect
export const typewriterContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.03,
    },
  },
}

export const typewriterChar: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}

// For task card spawn burst
export const taskSpawnVariants: Variants = {
  hidden: { scale: 0, rotate: -10, opacity: 0 },
  visible: (i: number) => ({
    scale: 1,
    rotate: 0,
    opacity: 1,
    x: (i - 2) * 100,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 20,
      delay: i * 0.1,
    },
  }),
}

// For phase node pulse
export const pulseVariants: Variants = {
  initial: { scale: 1 },
  pulse: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
}

// For checkmark draw
export const checkmarkVariants: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.3, ease: "easeOut" },
      opacity: { duration: 0.1 },
    },
  },
}

// For feedback loop arrow
export const arrowDrawVariants: Variants = {
  hidden: { pathLength: 0 },
  visible: {
    pathLength: 1,
    transition: {
      duration: 1,
      ease: "easeInOut",
    },
  },
}

// Terminal animation defaults
export const terminalDefaults = {
  backgroundColor: "#0D0D0D",
  textColor: "#E5E5E5",
  greenAccent: "#00FF41",
  yellowAccent: "#FFD93D",
  redAccent: "#FF4444",
  blueAccent: "#0366D6",
}
