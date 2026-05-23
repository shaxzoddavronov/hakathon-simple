import {
  forwardRef,
  type ComponentPropsWithoutRef,
  type ElementType,
  type ForwardedRef,
  type ReactElement,
} from "react";
import { cn } from "@/lib/cn";

/**
 * `<GlassPanel>` — the **only** place in the codebase that owns the
 * Neural Dark glassmorphism recipe (backdrop blur + translucent surface
 * + low-opacity outline + soft elevation). Every card, modal, message
 * bubble, and chart frame composes this; do not inline the glass classes
 * elsewhere (see CLAUDE.md §Design system).
 */

const GLASS_CLASSES =
  // depth + translucency
  "backdrop-blur-xl bg-surface-container/40 " +
  // 1px low-opacity outline per DESIGN.md §Cards
  "border border-outline/20 " +
  // soft-technical corner radius — uses Tailwind `2xl` (1rem) for large panels
  "rounded-2xl " +
  // luminous elevation; not a hard shadow
  "shadow-lg";

type PolymorphicProps<T extends ElementType> = {
  as?: T;
  className?: string;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "className">;

type GlassPanelComponent = <T extends ElementType = "div">(
  props: PolymorphicProps<T> & { ref?: ForwardedRef<Element> },
) => ReactElement | null;

export const GlassPanel = forwardRef(function GlassPanel<
  T extends ElementType = "div",
>(
  { as, className, ...rest }: PolymorphicProps<T>,
  ref: ForwardedRef<Element>,
) {
  const Component = (as ?? "div") as ElementType;
  return (
    <Component ref={ref} className={cn(GLASS_CLASSES, className)} {...rest} />
  );
}) as GlassPanelComponent;

export default GlassPanel;
