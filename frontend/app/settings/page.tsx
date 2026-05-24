"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { api, getToken } from "@/lib/api";

type SettingsOut = {
  vllm_endpoint: string;
  vllm_model_chat: string;
  vllm_model_profile: string;
  has_token: boolean;
  available_models: string[];
};

export default function SettingsPage() {
  const router = useRouter();
  const [endpoint, setEndpoint] = useState("");
  const [token, setToken] = useState("");
  const [modelChat, setModelChat] = useState("");
  const [modelProfile, setModelProfile] = useState("");
  const [available, setAvailable] = useState<string[]>([]);
  const [hasToken, setHasToken] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function apply(d: SettingsOut) {
    setEndpoint(d.vllm_endpoint);
    setModelChat(d.vllm_model_chat);
    setModelProfile(d.vllm_model_profile);
    setAvailable(d.available_models);
    setHasToken(d.has_token);
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<SettingsOut>("/settings")
      .then((d) => {
        apply(d);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load");
        setLoading(false);
      });
  }, [router]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const body: Record<string, string> = {
        vllm_endpoint: endpoint,
        vllm_model_chat: modelChat,
        vllm_model_profile: modelProfile,
      };
      if (token.trim()) body.vllm_token = token.trim();
      const d = await api<SettingsOut>("/settings", {
        method: "PUT",
        body: JSON.stringify(body),
      });
      apply(d);
      setToken("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-container-margin py-8 space-y-5">
      <header>
        <p className="font-mono text-label-caps uppercase text-on-surface-variant">
          Settings
        </p>
        <h1 className="font-headline text-headline-lg text-on-surface mt-1">
          Inference target
        </h1>
        <p className="text-on-surface-variant text-sm mt-1">
          QueryMind talks to an OpenAI-compatible vLLM endpoint. The{" "}
          <span className="text-primary-container">chat</span> model powers the
          interactive agent; the{" "}
          <span className="text-primary-container">learning</span> model runs the
          database-understanding pass when you connect or re-profile a database.
        </p>
      </header>

      {loading ? (
        <GlassPanel className="px-5 py-4 text-on-surface-variant">Loading…</GlassPanel>
      ) : (
        <form onSubmit={save}>
          <GlassPanel className="qm-gradient-border p-6 space-y-6">
            <Field label="vLLM endpoint">
              <input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="http://host:8080/v1"
                className="qm-underline w-full font-mono text-sm"
              />
            </Field>

            <Field label={`API token${hasToken ? " (set — leave blank to keep)" : ""}`}>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={hasToken ? "•••••••••• (stored)" : "paste token"}
                className="qm-underline w-full font-mono text-sm"
              />
            </Field>

            <Field label="Chat model (fast)">
              <ModelInput value={modelChat} onChange={setModelChat} options={available} />
            </Field>

            <Field label="Learning model (database understanding)">
              <ModelInput value={modelProfile} onChange={setModelProfile} options={available} />
            </Field>

            {error ? <div className="text-error text-sm">{error}</div> : null}
            {saved ? (
              <div className="text-tertiary text-sm flex items-center gap-2">
                <span className="qm-pulse-dot" /> Saved.
              </div>
            ) : null}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-primary-container text-on-primary-container px-6 py-2.5 font-semibold qm-glow disabled:opacity-50 transition hover:opacity-90"
              >
                {saving ? "Saving…" : "Save settings"}
              </button>
            </div>
          </GlassPanel>
        </form>
      )}
    </main>
  );
}

function ModelInput({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  if (options.length > 0) {
    const opts = options.includes(value) ? options : [value, ...options].filter(Boolean);
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="qm-underline w-full font-mono text-sm"
      >
        {opts.map((o) => (
          <option key={o} value={o} className="bg-surface">
            {o}
          </option>
        ))}
      </select>
    );
  }
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="model id"
      className="qm-underline w-full font-mono text-sm"
    />
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
