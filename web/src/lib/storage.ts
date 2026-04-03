/**
 * SSR-safe storage utilities
 * 
 * These wrappers ensure localStorage and sessionStorage are only accessed
 * in the browser environment, preventing "localStorage is not defined" errors
 * during server-side rendering.
 */

/**
 * Safely get an item from localStorage
 * @param key - The storage key
 * @returns The stored value or null if not found or during SSR
 */
export function getLocalStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch (error) {
    console.error(`Failed to read from localStorage (key: ${key}):`, error);
    return null;
  }
}

/**
 * Safely set an item in localStorage
 * @param key - The storage key
 * @param value - The value to store
 */
export function setLocalStorage(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    console.error(`Failed to write to localStorage (key: ${key}):`, error);
  }
}

/**
 * Safely remove an item from localStorage
 * @param key - The storage key
 */
export function removeLocalStorage(key: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.error(`Failed to remove from localStorage (key: ${key}):`, error);
  }
}

/**
 * Safely get an item from sessionStorage
 * @param key - The storage key
 * @returns The stored value or null if not found or during SSR
 */
export function getSessionStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(key);
  } catch (error) {
    console.error(`Failed to read from sessionStorage (key: ${key}):`, error);
    return null;
  }
}

/**
 * Safely set an item in sessionStorage
 * @param key - The storage key
 * @param value - The value to store
 */
export function setSessionStorage(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(key, value);
  } catch (error) {
    console.error(`Failed to write to sessionStorage (key: ${key}):`, error);
  }
}

/**
 * Safely remove an item from sessionStorage
 * @param key - The storage key
 */
export function removeSessionStorage(key: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(key);
  } catch (error) {
    console.error(`Failed to remove from sessionStorage (key: ${key}):`, error);
  }
}
