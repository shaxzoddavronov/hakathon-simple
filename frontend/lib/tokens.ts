/**
 * Neural Dark design tokens — single source of truth at runtime for code
 * paths that can't reach Tailwind classes (Recharts series colors, inline
 * styles, SVG fills, canvas, etc.). Mirror of ui_images/DESIGN.md.
 *
 * Keep this file, `tailwind.config.ts`, and `app/globals.css` in lockstep:
 * the YAML in DESIGN.md is the spec; all three are derived projections.
 */

export const colors = {
  surface: "#02132d",
  "surface-dim": "#02132d",
  "surface-bright": "#2a3955",
  "surface-container-lowest": "#000e26",
  "surface-container-low": "#0b1b35",
  "surface-container": "#0f1f3a",
  "surface-container-high": "#1b2a45",
  "surface-container-highest": "#263550",
  "on-surface": "#d7e2ff",
  "on-surface-variant": "#bbc9cf",
  "inverse-surface": "#d7e2ff",
  "inverse-on-surface": "#21304c",
  outline: "#859398",
  "outline-variant": "#3c494e",
  "surface-tint": "#3cd7ff",
  primary: "#a8e8ff",
  "on-primary": "#003642",
  "primary-container": "#00d4ff",
  "on-primary-container": "#00586b",
  "inverse-primary": "#00677e",
  secondary: "#d2bbff",
  "on-secondary": "#3f008e",
  "secondary-container": "#6001d1",
  "on-secondary-container": "#c9aeff",
  tertiary: "#00ff88",
  "on-tertiary": "#003919",
  "tertiary-container": "#00df76",
  "on-tertiary-container": "#005d2d",
  error: "#ffb4ab",
  "on-error": "#690005",
  "error-container": "#93000a",
  "on-error-container": "#ffdad6",
  "primary-fixed": "#b4ebff",
  "primary-fixed-dim": "#3cd7ff",
  "on-primary-fixed": "#001f27",
  "on-primary-fixed-variant": "#004e5f",
  "secondary-fixed": "#eaddff",
  "secondary-fixed-dim": "#d2bbff",
  "on-secondary-fixed": "#25005a",
  "on-secondary-fixed-variant": "#5a00c6",
  "tertiary-fixed": "#60ff99",
  "tertiary-fixed-dim": "#00e479",
  "on-tertiary-fixed": "#00210c",
  "on-tertiary-fixed-variant": "#005228",
  background: "#02132d",
  "on-background": "#d7e2ff",
  "surface-variant": "#263550",
} as const;

export type ColorToken = keyof typeof colors;

export const typography = {
  "headline-xl": {
    fontFamily: "Space Grotesk",
    fontSize: "48px",
    fontWeight: "700",
    lineHeight: "1.1",
    letterSpacing: "-0.02em",
  },
  "headline-lg": {
    fontFamily: "Space Grotesk",
    fontSize: "32px",
    fontWeight: "600",
    lineHeight: "1.2",
    letterSpacing: "-0.01em",
  },
  "headline-lg-mobile": {
    fontFamily: "Space Grotesk",
    fontSize: "24px",
    fontWeight: "600",
    lineHeight: "1.2",
  },
  "body-md": {
    fontFamily: "Inter",
    fontSize: "16px",
    fontWeight: "400",
    lineHeight: "1.6",
  },
  "body-sm": {
    fontFamily: "Inter",
    fontSize: "14px",
    fontWeight: "400",
    lineHeight: "1.5",
  },
  "data-mono": {
    fontFamily: "JetBrains Mono",
    fontSize: "14px",
    fontWeight: "500",
    lineHeight: "1.4",
    letterSpacing: "0.02em",
  },
  "label-caps": {
    fontFamily: "JetBrains Mono",
    fontSize: "12px",
    fontWeight: "700",
    lineHeight: "1.2",
    letterSpacing: "0.1em",
  },
} as const;

export type TypographyToken = keyof typeof typography;

export const rounded = {
  sm: "0.125rem",
  DEFAULT: "0.25rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  full: "9999px",
} as const;

export const spacing = {
  base: "8px",
  "container-margin": "24px",
  gutter: "16px",
  "stack-sm": "4px",
  "stack-md": "12px",
  "stack-lg": "24px",
} as const;

/**
 * Charts and KPIs cycle through these tokens for series colors.
 * Order: primary cyan → secondary violet → tertiary green → primary-fixed-dim
 * → secondary-fixed-dim → tertiary-fixed-dim. Tuned for the dark surface.
 */
export const chartPalette: readonly string[] = [
  colors["primary-container"],
  colors["secondary-container"],
  colors["tertiary-container"],
  colors["primary-fixed-dim"],
  colors["secondary-fixed-dim"],
  colors["tertiary-fixed-dim"],
] as const;

export const tokens = { colors, typography, rounded, spacing, chartPalette };
export default tokens;
