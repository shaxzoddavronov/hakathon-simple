import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * `cn(...)` — Tailwind-aware className composer.
 * Resolves conditional class arrays (clsx) then dedupes conflicting
 * Tailwind utilities (twMerge) so callers can pass overrides as a single
 * `className` prop without worrying about precedence.
 */
export const cn = (...args: ClassValue[]): string => twMerge(clsx(args));
