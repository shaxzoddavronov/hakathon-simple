"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearToken, getToken } from "@/lib/api";
import { BellIcon, GearIcon, SearchIcon, SparkIcon } from "@/components/icons";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/chat", label: "Neural Engine" },
  { href: "/settings", label: "Datasets" },
];

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();

  function signOut() {
    clearToken();
    router.push("/login");
  }

  // Header isn't useful on auth pages.
  if (pathname === "/login" || pathname === "/register") return null;

  const authed = typeof window !== "undefined" && Boolean(getToken());

  return (
    <header className="sticky top-0 z-30 border-b border-outline/15 bg-surface/70 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-container-margin py-3 flex items-center gap-6">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary-container/20 text-primary-container qm-glow">
            <SparkIcon width={18} height={18} />
          </span>
          <span className="font-headline text-lg tracking-tight text-on-surface">
            QueryMind <span className="text-primary-container">AI</span>
          </span>
        </Link>

        {/* Primary nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV.map((n) => {
            const active =
              pathname === n.href ||
              (n.href !== "/" && pathname.startsWith(n.href));
            return (
              <Link
                key={n.href}
                href={n.href}
                className={
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition " +
                  (active
                    ? "bg-primary-container/15 text-primary-container qm-glow"
                    : "text-on-surface-variant hover:text-on-surface")
                }
              >
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1" />

        {/* Search */}
        <div className="hidden lg:flex items-center gap-2 rounded-lg border border-outline/20 bg-surface-container/40 px-3 py-1.5 text-on-surface-variant w-56">
          <SearchIcon width={16} height={16} />
          <input
            placeholder="Global search…"
            className="bg-transparent text-sm outline-none placeholder:text-on-surface-variant/60 w-full text-on-surface"
          />
        </div>

        {/* Actions */}
        <button
          aria-label="Notifications"
          className="grid h-9 w-9 place-items-center rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container/50 transition"
        >
          <BellIcon />
        </button>
        <Link
          href="/settings"
          aria-label="Settings"
          className="grid h-9 w-9 place-items-center rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container/50 transition"
        >
          <GearIcon />
        </Link>
        {authed ? (
          <button
            onClick={signOut}
            className="ml-1 grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-primary-container to-secondary-container text-on-primary-container font-headline text-sm qm-glow"
            title="Sign out"
          >
            Q
          </button>
        ) : (
          <Link
            href="/login"
            className="ml-1 px-3 py-1.5 rounded-lg text-sm bg-primary-container text-on-primary-container font-semibold qm-glow"
          >
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
