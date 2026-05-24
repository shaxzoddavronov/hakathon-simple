"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { DatabaseIcon, PlusIcon, TableIcon, TrendIcon } from "@/components/icons";
import { api, getToken } from "@/lib/api";

type WorkspaceOut = {
  id: string;
  name: string;
  dialect: string;
  status: string;
};

const STATUS_TINT: Record<string, string> = {
  pending: "text-on-surface-variant",
  profiling: "text-secondary",
  ready: "text-tertiary",
  error: "text-error",
  auth_error: "text-error",
};

// Left accent bar / glow color, cycled per card (cyan → amber → violet).
const ACCENTS = ["#00d4ff", "#ffb020", "#6001d1"];

function setActiveWorkspace(id: string, name: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("qm_active_ws_id", id);
  window.localStorage.setItem("qm_active_ws_name", name);
}

export default function WorkspacesPage() {
  const router = useRouter();
  const [items, setItems] = useState<WorkspaceOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<WorkspaceOut[]>("/workspaces")
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
  }, [router]);

  function openChat(w: WorkspaceOut) {
    setActiveWorkspace(w.id, w.name);
    router.push("/chat");
  }

  const ready = items?.filter((w) => w.status === "ready").length ?? 0;

  return (
    <main className="mx-auto max-w-7xl px-container-margin py-8">
      <header className="mb-8">
        <h1 className="font-headline text-headline-lg text-on-surface">
          Your Workspaces
        </h1>
        <p className="text-on-surface-variant mt-1 max-w-2xl">
          Select an active environment to begin natural-language querying, or
          create a new instance to expand your data intelligence network.
        </p>
      </header>

      {error ? (
        <GlassPanel className="px-5 py-4 text-error">{error}</GlassPanel>
      ) : items === null ? (
        <GlassPanel className="px-5 py-4 text-on-surface-variant">Loading…</GlassPanel>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {items.map((w, i) => {
              const accent = ACCENTS[i % ACCENTS.length];
              return (
                <GlassPanel
                  key={w.id}
                  className="relative overflow-hidden p-5 flex flex-col"
                >
                  {/* accent bar */}
                  <span
                    className="absolute left-0 top-0 h-full w-1"
                    style={{ background: accent, boxShadow: `0 0 12px ${accent}` }}
                  />
                  <div className="flex items-start justify-between">
                    <span
                      className="grid h-10 w-10 place-items-center rounded-lg"
                      style={{ background: `${accent}22`, color: accent }}
                    >
                      <DatabaseIcon />
                    </span>
                    <span
                      className={
                        "font-mono text-label-caps uppercase " +
                        (STATUS_TINT[w.status] ?? "text-on-surface-variant")
                      }
                    >
                      {w.status}
                    </span>
                  </div>

                  <h2 className="font-headline text-lg text-on-surface mt-4">
                    {w.name}
                  </h2>
                  <p className="font-mono text-data-mono text-on-surface-variant mt-1 uppercase">
                    {w.dialect}
                  </p>

                  <div className="flex gap-2 mt-5 pt-1">
                    <Link
                      href={`/workspaces/${w.id}/schema`}
                      className="flex-1 text-center rounded-lg border border-outline/30 px-3 py-2 text-sm text-on-surface hover:border-primary-container/60 hover:text-primary-container transition"
                    >
                      Explore Schema
                    </Link>
                    <button
                      onClick={() => openChat(w)}
                      className="flex-1 rounded-lg px-3 py-2 text-sm font-semibold text-on-primary-container qm-glow transition hover:opacity-90"
                      style={{ background: accent }}
                    >
                      Open Chat
                    </button>
                  </div>
                </GlassPanel>
              );
            })}

            {/* New workspace */}
            <Link href="/workspaces/new" className="group">
              <GlassPanel className="h-full min-h-[200px] p-5 flex flex-col items-center justify-center text-center border-dashed border-outline/30 hover:border-primary-container/60 transition">
                <span className="grid h-12 w-12 place-items-center rounded-full border border-outline/30 text-on-surface-variant group-hover:text-primary-container group-hover:border-primary-container/60 group-hover:qm-glow transition">
                  <PlusIcon width={24} height={24} />
                </span>
                <span className="font-headline text-lg text-on-surface mt-4">
                  New Workspace
                </span>
                <span className="text-on-surface-variant text-sm mt-1">
                  Initialize a new data stream
                </span>
              </GlassPanel>
            </Link>
          </div>

          {/* System status strip */}
          <GlassPanel className="mt-6 px-6 py-4 flex flex-wrap items-center gap-x-10 gap-y-3">
            <div className="font-mono text-label-caps uppercase text-on-surface-variant">
              System Status
            </div>
            <Stat icon={<TableIcon width={16} height={16} />} value={String(items.length)} label="Workspaces" />
            <Stat icon={<TrendIcon width={16} height={16} />} value={String(ready)} label="Ready" />
            <Stat value="local" label="vLLM Engine" />
            <div className="flex-1" />
            <div className="flex items-center gap-2 text-tertiary">
              <span className="qm-pulse-dot" />
              <span className="font-mono text-data-mono">Local Engine Active</span>
            </div>
          </GlassPanel>
        </>
      )}
    </main>
  );
}

function Stat({
  icon,
  value,
  label,
}: {
  icon?: React.ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {icon ? <span className="text-primary-container">{icon}</span> : null}
      <div>
        <div className="font-headline text-on-surface leading-none">{value}</div>
        <div className="font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
          {label}
        </div>
      </div>
    </div>
  );
}
