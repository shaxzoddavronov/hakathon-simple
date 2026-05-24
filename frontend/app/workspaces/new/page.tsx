"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CodeBlock } from "@/components/CodeBlock";
import { GlassPanel } from "@/components/GlassPanel";
import { DatabaseIcon, TableIcon } from "@/components/icons";
import { api, getToken } from "@/lib/api";

type Dialect = "postgres" | "sqlite" | "clickhouse";

const GRANT_RECIPE: Record<Dialect, string> = {
  postgres: `-- Run as a superuser in the database you want to expose
CREATE ROLE querymind_ro LOGIN PASSWORD 'replace-me';
GRANT CONNECT ON DATABASE your_db TO querymind_ro;
GRANT USAGE  ON SCHEMA   public  TO querymind_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO querymind_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO querymind_ro;`,
  sqlite: `# QueryMind opens SQLite with mode=ro automatically.
# Make sure the file is readable by the backend process,
# and that no other process has it open for write at demo time.`,
  clickhouse: `-- Create a read-only ClickHouse user (run as an admin)
CREATE USER querymind_ro IDENTIFIED BY 'replace-me' SETTINGS readonly = 2;
GRANT SELECT ON your_db.* TO querymind_ro;
-- QueryMind also enforces readonly=2 on every query at runtime.`,
};

const ARCHS: { id: Dialect; label: string; icon: React.ReactNode }[] = [
  { id: "postgres", label: "PostgreSQL", icon: <DatabaseIcon width={28} height={28} /> },
  { id: "clickhouse", label: "ClickHouse", icon: <DatabaseIcon width={28} height={28} /> },
  { id: "sqlite", label: "SQLite", icon: <TableIcon width={28} height={28} /> },
];

// Default port per SQL dialect.
const DEFAULT_PORT: Record<string, string> = {
  postgres: "5432",
  clickhouse: "8123",
};

export default function NewWorkspacePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [dialect, setDialect] = useState<Dialect>("postgres");
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState("5432");
  const [dbName, setDbName] = useState("");
  const [path, setPath] = useState("");
  const [ssl, setSsl] = useState(false);
  const [user, setUser] = useState("querymind_ro");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [probing, setProbing] = useState(false);
  const [probe, setProbe] = useState<{
    reachable: boolean;
    can_write: boolean;
    message: string;
  } | null>(null);

  if (typeof window !== "undefined" && !getToken()) {
    router.replace("/login");
  }

  function buildConn() {
    const connection_meta =
      dialect === "sqlite"
        ? { path }
        : { host, port: Number(port), db_name: dbName, ssl };
    const credentials = dialect === "sqlite" ? {} : { user, password };
    return { connection_meta, credentials };
  }

  async function testConnection() {
    setProbe(null);
    setError(null);
    setProbing(true);
    try {
      const { connection_meta, credentials } = buildConn();
      const result = await api<{
        reachable: boolean;
        can_write: boolean;
        message: string;
      }>("/workspaces/probe", {
        method: "POST",
        body: JSON.stringify({ dialect, connection_meta, credentials }),
      });
      setProbe(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Probe failed");
    } finally {
      setProbing(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { connection_meta, credentials } = buildConn();
      const auth_kind = dialect === "sqlite" ? "none" : "password";
      await api("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name, dialect, connection_meta, credentials, auth_kind }),
      });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-container-margin py-10">
      <GlassPanel className="qm-gradient-border p-7 sm:p-8">
        {/* Setup phase header */}
        <div className="flex items-center justify-between font-mono text-label-caps uppercase text-on-surface-variant">
          <span>Setup Phase</span>
          <span>Workspace · Read-only</span>
        </div>
        <div className="mt-2 h-0.5 w-full rounded-full bg-surface-container-high/60 overflow-hidden">
          <div className="qm-sweep h-full w-1/3" />
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[11px] uppercase tracking-wider">
          <span className="text-primary-container">Identity</span>
          <span className="text-on-surface-variant">Connection</span>
          <span className="text-on-surface-variant">Intelligence</span>
        </div>

        <form onSubmit={submit} className="mt-8 space-y-8">
          {/* Workspace definition */}
          <div>
            <p className="font-mono text-label-caps uppercase text-on-surface-variant mb-2">
              Workspace Definition
            </p>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name your workspace…"
              className="qm-underline w-full font-headline text-2xl"
            />
          </div>

          {/* Architecture selector */}
          <div>
            <p className="text-on-surface mb-3">Select primary data architecture</p>
            <div className="grid grid-cols-3 gap-4">
              {ARCHS.map((a) => {
                const active = dialect === a.id;
                return (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => {
                      setDialect(a.id);
                      if (DEFAULT_PORT[a.id]) setPort(DEFAULT_PORT[a.id]!);
                    }}
                    className={
                      "rounded-lg border p-6 flex flex-col items-center gap-3 transition " +
                      (active
                        ? "border-primary-container/70 bg-primary-container/10 text-primary-container qm-glow"
                        : "border-outline/25 text-on-surface-variant hover:border-outline/50")
                    }
                  >
                    {a.icon}
                    <span className="font-mono text-sm tracking-wide">{a.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Connection */}
          <div className="space-y-5">
            <p className="font-mono text-label-caps uppercase text-on-surface-variant">
              Connection
            </p>
            {dialect !== "sqlite" ? (
              <>
                <Field label="Host">
                  <input required value={host} onChange={(e) => setHost(e.target.value)} className="qm-underline w-full" />
                </Field>
                <div className="grid grid-cols-2 gap-5">
                  <Field label="Port">
                    <input required type="number" value={port} onChange={(e) => setPort(e.target.value)} className="qm-underline w-full" />
                  </Field>
                  <Field label="Database">
                    <input required value={dbName} onChange={(e) => setDbName(e.target.value)} className="qm-underline w-full" />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-5">
                  <Field label="User">
                    <input required value={user} onChange={(e) => setUser(e.target.value)} className="qm-underline w-full" />
                  </Field>
                  <Field label="Password">
                    <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="qm-underline w-full" />
                  </Field>
                </div>
                <label className="flex items-center gap-2 text-sm text-on-surface-variant">
                  <input type="checkbox" checked={ssl} onChange={(e) => setSsl(e.target.checked)} />
                  Require TLS (ssl=require)
                </label>
              </>
            ) : (
              <Field label="SQLite file path">
                <input
                  required
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="/var/lib/querymind/sample.db"
                  className="qm-underline w-full"
                />
              </Field>
            )}
          </div>

          {error ? <div className="text-error text-sm">{error}</div> : null}
          {probe ? (
            <div
              className={
                "rounded-lg px-4 py-3 text-sm border " +
                (!probe.reachable || probe.can_write
                  ? "border-error/40 bg-error-container/20 text-error"
                  : "border-tertiary/40 bg-tertiary/10 text-tertiary")
              }
            >
              {probe.message}
            </div>
          ) : null}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={testConnection}
              disabled={probing}
              className="rounded-lg border border-outline/30 text-on-surface px-5 py-2.5 font-semibold disabled:opacity-50 hover:border-primary-container/60 hover:text-primary-container transition"
            >
              {probing ? "Testing…" : "Test connection"}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-primary-container text-on-primary-container px-7 py-2.5 font-semibold qm-glow disabled:opacity-50 transition hover:opacity-90"
            >
              {busy ? "Creating…" : "Continue"}
            </button>
          </div>
        </form>
      </GlassPanel>

      <GlassPanel className="mt-5 px-6 py-5">
        <p className="font-mono text-label-caps uppercase text-on-surface-variant mb-2">
          Read-only setup recipe · {dialect}
        </p>
        <CodeBlock language={dialect} code={GRANT_RECIPE[dialect]} />
      </GlassPanel>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="font-mono text-[11px] uppercase tracking-wider text-on-surface-variant">
        {label}
      </span>
      {children}
    </label>
  );
}
