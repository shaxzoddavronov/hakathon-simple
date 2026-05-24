"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { SparkIcon } from "@/components/icons";
import { login, registerUser } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await registerUser(email, password);
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-20">
      <div className="flex items-center justify-center gap-2 mb-8">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary-container/20 text-primary-container qm-glow">
          <SparkIcon width={20} height={20} />
        </span>
        <span className="font-headline text-xl tracking-tight text-on-surface">
          QueryMind <span className="text-primary-container">AI</span>
        </span>
      </div>
      <GlassPanel className="qm-gradient-border px-7 py-7">
        <h1 className="font-headline text-2xl mb-1 text-on-surface">Initialize Identity</h1>
        <p className="text-on-surface-variant text-sm mb-6">
          Create your account to connect a database.
        </p>
        <form onSubmit={submit} className="space-y-5">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="qm-underline w-full"
          />
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (≥8 chars)"
            className="qm-underline w-full"
          />
          {error ? <div className="text-error text-sm">{error}</div> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary-container text-on-primary-container py-2.5 font-semibold qm-glow hover:opacity-90 disabled:opacity-50 transition"
          >
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <div className="mt-5 text-sm text-on-surface-variant">
          Have an account?{" "}
          <Link href="/login" className="text-primary-container hover:underline">
            Sign in
          </Link>
        </div>
      </GlassPanel>
    </main>
  );
}
