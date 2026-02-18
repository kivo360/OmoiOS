"use client";

import { useEffect } from "react";
import { initOnboardingDebug } from "@/lib/onboarding/debug";

/**
 * Client component that initializes onboarding debug tools on mount.
 * Only active in development or when localStorage debug flag is set.
 */
export function OnboardingDebugInit() {
  useEffect(() => {
    initOnboardingDebug();
  }, []);

  // This component renders nothing
  return null;
}
