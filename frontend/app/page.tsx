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
  table_count?: number | null;
  last_synced_at?: string | null;
};

function timeAgo(iso?: string | null): string {
  if (!iso) return "never";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "never";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const STATUS_TINT: Record<string, string> = {
  pending: "text-on-surface-variant",
  profiling: "text-secondary",
  ready: "text-tertiary",
  error: "text-error",
  auth_error: "text-error",
};

// Left accent + button color, cycled per card (cyan → amber → violet).
// `text` is the readable foreground for a solid button of color `c`.
const ACCENTS = [
  { c: "#00d4ff", text: "#02132d" },
  { c: "#ffb020", text: "#02132d" },
  { c: "#6001d1", text: "#ffffff" },
];

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
              const accent = ACCENTS[i % ACCENTS.length]!;
              return (
                <GlassPanel
                  key={w.id}
                  className="relative overflow-hidden p-5 flex flex-col"
                >
                  {/* accent bar */}
                  <span
                    className="absolute left-0 top-0 h-full w-1"
                    style={{ background: accent.c, boxShadow: `0 0 12px ${accent.c}` }}
                  />
                  <div className="flex items-start justify-between">
                    <span
                      className="grid h-10 w-10 place-items-center rounded-lg"
                      style={{ background: `${accent.c}22`, color: accent.c }}
                    >
                      <DatabaseIcon />
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant border border-outline/25 rounded-full px-2 py-0.5">
                      {w.dialect}
                    </span>
                  </div>

                  <h2 className="font-headline text-lg text-on-surface mt-4">
                    {w.name}
                  </h2>
                  <div className="mt-1 space-y-0.5 font-mono text-data-mono text-on-surface-variant">
                    <div>
                      {w.table_count != null ? `${w.table_count} tables` : "— tables"}
                    </div>
                    <div>Last synced {timeAgo(w.last_synced_at)}</div>
                  </div>
                  <div
                    className={
                      "mt-2 font-mono text-[11px] uppercase tracking-wider " +
                      (STATUS_TINT[w.status] ?? "text-on-surface-variant")
                    }
                  >
                    ● {w.status}
                  </div>

                  <div className="flex gap-2 mt-5 pt-1">
                    <Link
                      href={`/workspaces/${w.id}/schema`}
                      className="flex-1 text-center rounded-lg border border-outline/30 px-3 py-2 text-sm text-on-surface hover:border-primary-container/60 hover:text-primary-container transition"
                    >
                      Explore Schema
                    </Link>
                    <button
                      onClick={() => openChat(w)}
                      className="flex-1 rounded-lg px-3 py-2 text-sm font-semibold qm-glow transition hover:opacity-90"
                      style={{ background: accent.c, color: accent.text }}
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
            <div className="text-right max-w-xs">
              <div className="flex items-center justify-end gap-2 text-tertiary">
                <span className="qm-pulse-dot" />
                <span className="font-mono text-data-mono">Live Engine Active</span>
              </div>
              <p className="text-on-surface-variant text-xs mt-1">
                QueryMind processes queries locally across {items.length}{" "}
                workspace{items.length === 1 ? "" : "s"}. All systems nominal.
              </p>
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
