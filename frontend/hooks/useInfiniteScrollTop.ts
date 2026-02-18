"use client";

import { useEffect, useRef, useCallback, useState } from "react";

interface UseInfiniteScrollTopOptions {
  /**
   * Whether there are more items to load
   */
  hasMore: boolean;
  /**
   * Whether currently loading more items
   */
  isLoading: boolean;
  /**
   * Function to call when the sentinel becomes visible
   */
  onLoadMore: () => void | Promise<void>;
  /**
   * Cooldown period in ms between loads (default: 1500ms)
   * Prevents rapid-fire loads when scrolling to top
   */
  cooldownMs?: number;
  /**
   * Whether the hook is enabled (default: true)
   */
  enabled?: boolean;
  /**
   * Threshold for IntersectionObserver (0-1, default: 0.1)
   * How much of the sentinel needs to be visible to trigger
   */
  threshold?: number;
  /**
   * Root margin for IntersectionObserver (default: "100px")
   * Allows triggering before the sentinel is fully visible
   */
  rootMargin?: string;
}

interface UseInfiniteScrollTopReturn {
  /**
   * Ref to attach to the sentinel element at the top of the list
   */
  sentinelRef: React.RefObject<HTMLDivElement>;
  /**
   * Ref for the scroll container viewport
   */
  viewportRef: React.RefObject<HTMLDivElement>;
  /**
   * Whether we're in cooldown period
   */
  isInCooldown: boolean;
  /**
   * Call this before loading to capture scroll position
   */
  captureScrollPosition: () => void;
  /**
   * Call this after loading to restore scroll position
   */
  restoreScrollPosition: () => void;
}

/**
 * Custom hook for implementing infinite scroll at the TOP of a list.
 *
 * This is designed for "load older events" patterns where new content
 * is prepended to the list rather than appended.
 *
 * Features:
 * - IntersectionObserver-based detection (efficient, no scroll event spam)
 * - Cooldown mechanism to prevent rapid-fire loads
 * - Scroll position preservation helpers
 *
 * Usage:
 * ```tsx
 * const { sentinelRef, viewportRef, captureScrollPosition, restoreScrollPosition } = useInfiniteScrollTop({
 *   hasMore,
 *   isLoading,
 *   onLoadMore: async () => {
 *     captureScrollPosition()
 *     await loadMoreEvents()
 *     // Note: restoreScrollPosition should be called in a useEffect after state updates
 *   },
 * })
 *
 * return (
 *   <ScrollArea viewportRef={viewportRef}>
 *     <div ref={sentinelRef} className="h-1" /> {* Sentinel at top *}
 *     {events.map(event => <Event key={event.id} event={event} />)}
 *   </ScrollArea>
 * )
 * ```
 */
export function useInfiniteScrollTop({
  hasMore,
  isLoading,
  onLoadMore,
  cooldownMs = 1500,
  enabled = true,
  threshold = 0.1,
  rootMargin = "100px",
}: UseInfiniteScrollTopOptions): UseInfiniteScrollTopReturn {
  const sentinelRef = useRef<HTMLDivElement>(null!);
  const viewportRef = useRef<HTMLDivElement>(null!);
  const [isInCooldown, setIsInCooldown] = useState(false);
  const cooldownTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Store scroll position data
  const scrollDataRef = useRef<{
    scrollHeight: number;
    scrollTop: number;
  } | null>(null);

  // Capture current scroll position before loading more content
  const captureScrollPosition = useCallback(() => {
    if (viewportRef.current) {
      scrollDataRef.current = {
        scrollHeight: viewportRef.current.scrollHeight,
        scrollTop: viewportRef.current.scrollTop,
      };
    }
  }, []);

  // Restore scroll position after content is prepended
  // This keeps the user at the same visual position
  const restoreScrollPosition = useCallback(() => {
    if (viewportRef.current && scrollDataRef.current) {
      const newScrollHeight = viewportRef.current.scrollHeight;
      const heightDiff = newScrollHeight - scrollDataRef.current.scrollHeight;

      // Add the height difference to maintain visual position
      viewportRef.current.scrollTop =
        scrollDataRef.current.scrollTop + heightDiff;
      scrollDataRef.current = null;
    }
  }, []);

  // Start cooldown timer
  const startCooldown = useCallback(() => {
    setIsInCooldown(true);

    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
    }

    cooldownTimerRef.current = setTimeout(() => {
      setIsInCooldown(false);
      cooldownTimerRef.current = null;
    }, cooldownMs);
  }, [cooldownMs]);

  // Handle intersection
  const handleIntersection = useCallback(
    async (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;

      // Only trigger if:
      // 1. Sentinel is intersecting (visible)
      // 2. Not currently loading
      // 3. Not in cooldown
      // 4. Has more to load
      // 5. Hook is enabled
      if (
        entry.isIntersecting &&
        !isLoading &&
        !isInCooldown &&
        hasMore &&
        enabled
      ) {
        startCooldown();
        captureScrollPosition();
        await onLoadMore();
      }
    },
    [
      isLoading,
      isInCooldown,
      hasMore,
      enabled,
      startCooldown,
      captureScrollPosition,
      onLoadMore,
    ],
  );

  // Set up IntersectionObserver
  useEffect(() => {
    if (!enabled || !sentinelRef.current) return;

    const observer = new IntersectionObserver(handleIntersection, {
      root: viewportRef.current,
      rootMargin,
      threshold,
    });

    observer.observe(sentinelRef.current);

    return () => {
      observer.disconnect();
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
      }
    };
  }, [enabled, handleIntersection, rootMargin, threshold]);

  return {
    sentinelRef,
    viewportRef,
    isInCooldown,
    captureScrollPosition,
    restoreScrollPosition,
  };
}
