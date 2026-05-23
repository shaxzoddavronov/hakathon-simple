"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CodeBlock } from "@/components/CodeBlock";
import { GlassPanel } from "@/components/GlassPanel";
import { api, getToken } from "@/lib/api";

type Dialect = "postgres" | "sqlite";

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
      dialect === "postgres"
        ? { host, port: Number(port), db_name: dbName, ssl }
        : { path };
    const credentials = dialect === "postgres" ? { user, password } : {};
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
      const auth_kind = dialect === "postgres" ? "password" : "none";
      await api("/workspaces", {
        method: "POST",
        body: JSON.stringify({
          name,
          dialect,
          connection_meta,
          credentials,
          auth_kind,
        }),
      });
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <header>
        <p className="font-mono text-label-caps uppercase text-on-surface-variant">
          New workspace
        </p>
        <h1 className="font-headline text-headline-lg text-on-surface mt-1">
          Connect a database
        </h1>
        <p className="text-on-surface-variant text-sm mt-1">
          QueryMind runs read-only queries against this connection. Use a
          dedicated read-only role for production data.
        </p>
      </header>

      <form onSubmit={submit} className="space-y-4">
        <GlassPanel className="px-5 py-4 space-y-3">
          <Field label="Name">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Core_Analytics"
              className="w-full input"
            />
          </Field>
          <Field label="Dialect">
            <div className="flex gap-2">
              {(["postgres", "sqlite"] as Dialect[]).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDialect(d)}
                  className={
                    "px-3 py-1.5 rounded-xl text-sm " +
                    (dialect === d
                      ? "bg-primary-container/30 text-primary"
                      : "bg-surface-container-high/40 text-on-surface-variant")
                  }
                >
                  {d}
                </button>
              ))}
            </div>
          </Field>

          {dialect === "postgres" ? (
            <>
              <Field label="Host">
                <input
                  required
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  className="w-full input"
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Port">
                  <input
                    required
                    type="number"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    className="w-full input"
                  />
                </Field>
                <Field label="Database">
                  <input
                    required
                    value={dbName}
                    onChange={(e) => setDbName(e.target.value)}
                    className="w-full input"
                  />
                </Field>
              </div>
              <Field label="User">
                <input
                  required
                  value={user}
                  onChange={(e) => setUser(e.target.value)}
                  className="w-full input"
                />
              </Field>
              <Field label="Password">
                <input
                  required
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full input"
                />
              </Field>
              <label className="flex items-center gap-2 text-sm text-on-surface-variant">
                <input
                  type="checkbox"
                  checked={ssl}
                  onChange={(e) => setSsl(e.target.checked)}
                />
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
                className="w-full input"
              />
            </Field>
          )}

          {error ? <div className="text-error text-sm">{error}</div> : null}

          {probe ? (
            <div
              className={
                "rounded-xl px-4 py-3 text-sm border " +
                (!probe.reachable
                  ? "border-error/40 bg-error-container/20 text-error"
                  : probe.can_write
                    ? "border-error/40 bg-error-container/20 text-error"
                    : "border-tertiary/40 bg-tertiary/10 text-tertiary")
              }
            >
              {probe.message}
            </div>
          ) : null}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={testConnection}
              disabled={probing}
              className="flex-1 rounded-xl border border-outline/30 text-on-surface py-2 font-semibold disabled:opacity-50 hover:bg-surface-container-high/40"
            >
              {probing ? "Testing…" : "Test connection"}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="flex-1 rounded-xl bg-primary-container text-on-primary-container py-2 font-semibold disabled:opacity-50"
            >
              {busy ? "Creating…" : "Create workspace"}
            </button>
          </div>
        </GlassPanel>

        <GlassPanel className="px-5 py-4">
          <p className="text-on-surface-variant text-sm mb-2">
            Read-only setup recipe for {dialect}:
          </p>
          <CodeBlock language={dialect} code={GRANT_RECIPE[dialect]} />
        </GlassPanel>
      </form>

      <style jsx>{`
        :global(.input) {
          background: rgba(27, 42, 69, 0.6);
          border: 1px solid rgba(133, 147, 152, 0.2);
          border-radius: 0.75rem;
          padding: 0.5rem 1rem;
          color: #d7e2ff;
          outline: none;
        }
        :global(.input:focus) {
          border-color: #a8e8ff;
        }
      `}</style>
    </main>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs uppercase tracking-wider text-on-surface-variant">
        {label}
      </span>
      {children}
    </label>
  );
}
