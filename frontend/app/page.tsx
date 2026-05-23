import { GlassPanel } from "@/components/GlassPanel";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-container-margin py-stack-lg">
      <GlassPanel className="p-stack-lg">
        <p className="font-mono text-label-caps uppercase text-on-surface-variant">
          QueryMind AI
        </p>
        <h1 className="mt-stack-md font-headline text-headline-lg text-on-surface">
          QueryMind AI &mdash; workspaces grid coming in Wave 4.
        </h1>
        <p className="mt-stack-md font-body text-body-md text-on-surface-variant">
          Wave 1 scaffolding only: design tokens, base glass panel, and code
          block primitives.
        </p>
      </GlassPanel>
    </main>
  );
}
