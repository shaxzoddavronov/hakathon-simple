---
name: Neural Dark
colors:
  surface: '#02132d'
  surface-dim: '#02132d'
  surface-bright: '#2a3955'
  surface-container-lowest: '#000e26'
  surface-container-low: '#0b1b35'
  surface-container: '#0f1f3a'
  surface-container-high: '#1b2a45'
  surface-container-highest: '#263550'
  on-surface: '#d7e2ff'
  on-surface-variant: '#bbc9cf'
  inverse-surface: '#d7e2ff'
  inverse-on-surface: '#21304c'
  outline: '#859398'
  outline-variant: '#3c494e'
  surface-tint: '#3cd7ff'
  primary: '#a8e8ff'
  on-primary: '#003642'
  primary-container: '#00d4ff'
  on-primary-container: '#00586b'
  inverse-primary: '#00677e'
  secondary: '#d2bbff'
  on-secondary: '#3f008e'
  secondary-container: '#6001d1'
  on-secondary-container: '#c9aeff'
  tertiary: '#00ff88'
  on-tertiary: '#003919'
  tertiary-container: '#00df76'
  on-tertiary-container: '#005d2d'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b4ebff'
  primary-fixed-dim: '#3cd7ff'
  on-primary-fixed: '#001f27'
  on-primary-fixed-variant: '#004e5f'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#5a00c6'
  tertiary-fixed: '#60ff99'
  tertiary-fixed-dim: '#00e479'
  on-tertiary-fixed: '#00210c'
  on-tertiary-fixed-variant: '#005228'
  background: '#02132d'
  on-background: '#d7e2ff'
  surface-variant: '#263550'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  container-margin: 24px
  gutter: 16px
  stack-sm: 4px
  stack-md: 12px
  stack-lg: 24px
---

## Brand & Style

The design system is engineered for high-performance environments, evoking the atmosphere of a futuristic command center or a neural interface. The aesthetic is rooted in **Glassmorphism** and **Futuristic** design movements, emphasizing depth through translucency and bioluminescent accents. 

The target audience consists of power users, developers, and data analysts who require an immersive, focused workspace. The UI should feel like a living digital organism—responsive, precise, and sophisticated. Visual interest is driven by high-contrast neon accents against a deep, void-like background, utilizing a dot-grid texture to provide a sense of spatial scale and mathematical precision.

## Colors

The palette is anchored by a near-black atmospheric navy, providing a canvas where light is used as a functional tool rather than just decoration. 

- **Primary Accent (Electric Cyan):** Used for critical interactions, progress indicators, and primary action states.
- **Secondary Accent (Vivid Violet):** Used for depth, data visualization variety, and supplementary brand moments.
- **Surface Strategy:** Backgrounds utilize a subtle dot-grid pattern at 5% opacity. Surfaces are semi-transparent with a 1px low-opacity border to define boundaries without closing off the UI.
- **Functional Colors:** Bioluminescent green signifies success and system health, while amber is reserved for high-priority warnings.

## Typography

The typographic hierarchy balances technical utility with editorial flair. 

**Space Grotesk** is used for headlines to provide a geometric, futuristic rhythm. **Inter** handles the bulk of the reading experience, ensuring legibility in dense data environments. **JetBrains Mono** is the workhorse for technical metadata, "LCD-style" numerical readouts, and status labels, reinforcing the system's developer-centric DNA. Large headings should use tighter letter spacing to maintain a compact, "designed" feel.

## Layout & Spacing

This design system employs a **fluid 12-column grid** for main dashboard layouts, transitioning to a single-column stack on mobile devices. 

The spacing rhythm is built on an 8px base unit. Wide margins (24px+) are encouraged to allow the glassmorphic panels "room to breathe" against the dark background. Use consistent internal padding for glass cards (usually 24px) to ensure content does not feel crowded against the translucent edges. Content reflow follows a standard breakpoint system (640px, 1024px, 1440px).

## Elevation & Depth

Depth in the design system is achieved through light and transparency rather than traditional shadows.

1.  **Backdrop Blur:** All surface panels must implement a `backdrop-blur-md` (approx. 12px-16px) effect to maintain legibility over the dot-grid background.
2.  **Luminous Glows:** Primary active elements (buttons, active tabs) feature a diffused cyan glow (`0 0 15px rgba(0, 212, 255, 0.3)`).
3.  **Layering:** Surfaces are layered using Z-index stacking with increasing border brightness. Higher-level modals or popovers should have slightly more opaque background tints than base-level cards.
4.  **Gradient Borders:** High-priority containers or "featured" cards utilize an animated 1px gradient border transitioning from Cyan to Violet to imply energy and movement.

## Shapes

The shape language is "Soft-Technical." Elements use a 4px (0.25rem) base radius to ensure the UI feels modern and approachable, while still retaining the sharp precision of a high-tech instrument. 

Interactive components like buttons and tags follow this standard, while decorative "sensor" elements or data points may remain sharp (0px) to contrast with the UI shell. Large glass panels should use `rounded-lg` (8px) to soften the overall interface composition.

## Components

- **Buttons:** Primary buttons feature a solid Electric Cyan fill with black text; secondary buttons are ghost-style with a 1px Cyan border and a subtle hover glow.
- **Inputs:** Strictly "underline-style." No bounding boxes. The underline is #FFFFFF15 by default and animates to a 2px Electric Cyan line on focus, accompanied by a faint glow.
- **Cards:** Defined by the semi-transparent frosted glass surface (`#FFFFFF08`) and a 1px border. Use internal padding of 24px.
- **Chips/Status:** Small, JetBrains Mono labels. Success states use a "pulsing" bioluminescent green dot next to the text.
- **Lists:** Rows separated by 1px dimmed borders (`#FFFFFF05`). Hovering over a list item should trigger a subtle increase in the background opacity.
- **Progress Bars:** Utilize the Cyan-to-Violet gradient for the fill, with the background track set to a deep, semi-transparent grey.
- **Data Visuals:** Charts should use the primary and secondary accent colors, with grid lines set to minimum visibility to keep the focus on the bioluminescent data points.