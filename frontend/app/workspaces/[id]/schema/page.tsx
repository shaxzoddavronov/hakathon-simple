"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { SearchIcon, SparkIcon, TableIcon } from "@/components/icons";
import { api, getToken } from "@/lib/api";

type Sample = {
  distinct_values?: unknown[] | null;
  distinct_truncated?: boolean;
  numeric_stats?: Record<string, number> | null;
  sample_rows?: unknown[] | null;
  non_null_count?: number | null;
};
type Column = {
  name: string;
  data_type: string;
  nullable: boolean;
  is_pk?: boolean;
  is_id?: boolean;
  fk_to?: string | null;
};
type Table = {
  schema: string;
  name: string;
  columns: Column[];
  foreign_keys: { from_columns: string[]; to_table: string; to_columns: string[] }[];
  row_count_estimate?: number | null;
};
type Bundle = {
  dialect: string;
  tables: Table[];
  samples: Record<string, Record<string, Sample>>;
};
type Resp = {
  workspace_id: string;
  status: string;
  bundle: Bundle | null;
  message?: string;
  refreshed_at?: string;
};

export default function SchemaPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<Resp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Resp>(`/workspaces/${params.id}/schema`)
      .then((d) => {
        setData(d);
        const first = d.bundle?.tables[0];
        if (first) setSelected(`${first.schema}.${first.name}`);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [params.id, router]);

  const tables = data?.bundle?.tables ?? [];
  const filtered = useMemo(
    () => tables.filter((t) => t.name.toLowerCase().includes(filter.toLowerCase())),
    [tables, filter],
  );
  const selectedTable = tables.find((t) => `${t.schema}.${t.name}` === selected);
  const samples = (selected && data?.bundle?.samples[selected]) || {};

  function chatWithTable() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("qm_active_ws_id", params.id);
    }
    router.push("/chat");
  }

  if (error)
    return (
      <Shell>
        <GlassPanel className="px-5 py-4 text-error">{error}</GlassPanel>
      </Shell>
    );
  if (!data)
    return (
      <Shell>
        <GlassPanel className="px-5 py-4 text-on-surface-variant">Loading…</GlassPanel>
      </Shell>
    );
  if (!data.bundle)
    return (
      <Shell>
        <GlassPanel className="px-5 py-4">
          <div className="text-on-surface">Status: {data.status}</div>
          <div className="text-on-surface-variant text-sm mt-1">
            {data.message ?? "Bundle not available."}
          </div>
        </GlassPanel>
      </Shell>
    );

  return (
    <Shell>
      <div className="grid grid-cols-12 gap-5">
        {/* Sidebar */}
        <GlassPanel className="col-span-12 lg:col-span-3 p-3 lg:max-h-[78vh] overflow-y-auto">
          <div className="flex items-center gap-2 rounded-lg border border-outline/20 bg-surface-container/40 px-3 py-1.5 text-on-surface-variant">
            <SearchIcon width={16} height={16} />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Search tables…"
              className="bg-transparent text-sm outline-none w-full text-on-surface placeholder:text-on-surface-variant/60"
            />
          </div>
          <div className="font-mono text-[11px] uppercase tracking-wider text-on-surface-variant px-2 pt-3 pb-2">
            Schema Objects · {tables.length}
          </div>
          <ul className="space-y-0.5">
            {filtered.map((t) => {
              const qn = `${t.schema}.${t.name}`;
              const active = qn === selected;
              return (
                <li key={qn}>
                  <button
                    onClick={() => setSelected(qn)}
                    className={
                      "w-full flex items-center gap-2 text-left px-3 py-2 rounded-lg font-mono text-sm transition " +
                      (active
                        ? "bg-primary-container/15 text-primary-container qm-glow"
                        : "text-on-surface hover:bg-surface-container-high/30")
                    }
                  >
                    <TableIcon width={15} height={15} />
                    <span className="flex-1 truncate">{t.name}</span>
                    <span className="text-[11px] text-on-surface-variant">
                      {t.columns.length}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </GlassPanel>

        {/* Main */}
        <div className="col-span-12 lg:col-span-9 space-y-5">
          {selectedTable ? (
            <>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-headline text-2xl text-on-surface flex items-center gap-2">
                    {selectedTable.name}
                    <span className="font-mono text-[11px] uppercase tracking-wider text-on-surface-variant border border-outline/25 rounded px-2 py-0.5">
                      {data.bundle.dialect}
                    </span>
                  </h2>
                  <p className="text-on-surface-variant text-sm mt-1">
                    {selectedTable.row_count_estimate != null &&
                    selectedTable.row_count_estimate >= 0
                      ? `~${selectedTable.row_count_estimate.toLocaleString()} rows · `
                      : ""}
                    {selectedTable.columns.length} columns
                  </p>
                </div>
                <button
                  onClick={chatWithTable}
                  className="flex items-center gap-2 rounded-lg bg-primary-container text-on-primary-container px-4 py-2 text-sm font-semibold qm-glow hover:opacity-90 transition"
                >
                  <SparkIcon width={16} height={16} /> Chat with this table
                </button>
              </div>

              {/* Column cards */}
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {selectedTable.columns.map((c) => {
                  const s = samples[c.name];
                  return (
                    <GlassPanel key={c.name} className="p-4 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-mono text-on-surface">{c.name}</span>
                        <span className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant border border-outline/25 rounded px-1.5 py-0.5 shrink-0">
                          {c.data_type}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {c.is_pk ? <Badge tone="primary">PK</Badge> : null}
                        {c.is_id && !c.is_pk ? <Badge tone="secondary">ID</Badge> : null}
                        {c.fk_to ? <Badge tone="tertiary">→ {c.fk_to}</Badge> : null}
                        {c.nullable ? <Badge tone="muted">nullable</Badge> : null}
                      </div>
                      {s ? <SampleLine s={s} /> : null}
                    </GlassPanel>
                  );
                })}
              </div>

              {/* Semantic insight */}
              <GlassPanel className="qm-gradient-border p-5">
                <div className="flex items-center gap-2 font-mono text-label-caps uppercase text-primary-container mb-2">
                  <SparkIcon width={16} height={16} /> Semantic Insight
                </div>
                <p className="text-on-surface-variant text-sm">
                  {insightFor(selectedTable)}
                </p>
              </GlassPanel>
            </>
          ) : (
            <GlassPanel className="px-5 py-8 text-center text-on-surface-variant">
              Select a table to inspect.
            </GlassPanel>
          )}
        </div>
      </div>
    </Shell>
  );
}

function insightFor(t: Table): string {
  const fks = t.foreign_keys?.length ?? 0;
  const pk = t.columns.find((c) => c.is_pk)?.name;
  const parts: string[] = [];
  parts.push(`QueryMind profiled ${t.columns.length} columns in ${t.name}.`);
  if (pk) parts.push(`Primary key: ${pk}.`);
  if (fks > 0)
    parts.push(
      `${fks} foreign-key relationship${fks > 1 ? "s" : ""} link this table to others — joins are available to the planner.`,
    );
  else parts.push("No foreign keys detected on this table.");
  return parts.join(" ");
}

function SampleLine({ s }: { s: Sample }) {
  let body: string | null = null;
  if (s.distinct_values?.length) {
    body =
      "distinct: " +
      s.distinct_values.map((v) => JSON.stringify(v)).join(", ") +
      (s.distinct_truncated ? ", …" : "");
  } else if (s.numeric_stats) {
    body = Object.entries(s.numeric_stats)
      .map(([k, v]) => `${k}=${v}`)
      .join("  ");
  } else if (s.sample_rows?.length) {
    body = "e.g. " + s.sample_rows.map((v) => JSON.stringify(v)).join(", ");
  }
  if (!body) return null;
  return (
    <div className="font-mono text-[11px] text-on-surface-variant truncate" title={body}>
      {body}
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "primary" | "secondary" | "tertiary" | "muted";
}) {
  const tones: Record<string, string> = {
    primary: "text-primary-container border-primary-container/40",
    secondary: "text-secondary border-secondary/40",
    tertiary: "text-tertiary border-tertiary/40",
    muted: "text-on-surface-variant border-outline/30",
  };
  return (
    <span
      className={
        "font-mono text-[10px] uppercase tracking-wider rounded px-1.5 py-0.5 border " +
        tones[tone]
      }
    >
      {children}
    </span>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-7xl px-container-margin py-8 space-y-5">
      <header>
        <p className="font-mono text-label-caps uppercase text-on-surface-variant">
          Schema Explorer
        </p>
        <h1 className="font-headline text-headline-lg text-on-surface mt-1">
          Profiled schema
        </h1>
      </header>
      {children}
    </main>
  );
}
