/**
 * Safe localStorage wrapper that handles errors gracefully
 *
 * This handles cases where localStorage is not available:
 * - Private/Incognito mode with strict settings
 * - Safari ITP blocking third-party storage
 * - Iframe with blocked storage permissions
 * - localStorage quota exceeded
 */

import {
  createJSONStorage,
  type PersistStorage,
  type StorageValue,
} from "zustand/middleware";

// In-memory fallback when localStorage is not available
const memoryStorage = new Map<string, string>();

/**
 * Check if localStorage is available and accessible
 */
export function isLocalStorageAvailable(): boolean {
  if (typeof window === "undefined") return false;

  try {
    const testKey = "__storage_test__";
    window.localStorage.setItem(testKey, testKey);
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Safe localStorage getter - returns null if storage is blocked
 */
export function safeGetItem(key: string): string | null {
  if (typeof window === "undefined") return null;

  try {
    return localStorage.getItem(key);
  } catch {
    // Fallback to memory storage
    return memoryStorage.get(key) ?? null;
  }
}

/**
 * Safe localStorage setter - silently fails if storage is blocked
 */
export function safeSetItem(key: string, value: string): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(key, value);
  } catch {
    // Fallback to memory storage
    memoryStorage.set(key, value);
  }
}

/**
 * Safe localStorage remover - silently fails if storage is blocked
 */
export function safeRemoveItem(key: string): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.removeItem(key);
  } catch {
    // Fallback to memory storage
    memoryStorage.delete(key);
  }
}

/**
 * Create a Zustand-compatible storage object that handles errors
 * Use this with Zustand's persist middleware:
 *
 * @example
 * persist(
 *   (set, get) => ({ ... }),
 *   {
 *     name: 'my-store',
 *     storage: createSafeStorage(),
 *   }
 * )
 */
export function createSafeStorage<T>(): PersistStorage<T> {
  const storage = createJSONStorage<T>(() => ({
    getItem: (name: string): string | null => {
      return safeGetItem(name);
    },
    setItem: (name: string, value: string): void => {
      safeSetItem(name, value);
    },
    removeItem: (name: string): void => {
      safeRemoveItem(name);
    },
  }));

  // createJSONStorage can return undefined if window is undefined during SSR
  // In that case, provide a no-op storage that won't crash
  if (!storage) {
    return {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    };
  }

  return storage;
}
