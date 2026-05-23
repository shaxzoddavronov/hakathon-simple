"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearToken, getToken } from "@/lib/api";

const NAV = [
  { href: "/", label: "Workspaces" },
  { href: "/chat", label: "Chat" },
  { href: "/settings", label: "Settings" },
];

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();

  function signOut() {
    clearToken();
    router.push("/login");
  }

  // Header isn't useful on auth pages
  if (pathname === "/login" || pathname === "/register") return null;

  const authed = typeof window !== "undefined" && Boolean(getToken());

  return (
    <header className="sticky top-0 z-20 border-b border-outline/15 bg-surface/70 backdrop-blur-xl">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-headline text-on-surface text-lg tracking-tight">
          QueryMind <span className="text-primary">AI</span>
        </Link>
        <nav className="flex items-center gap-1">
          {NAV.map((n) => {
            const active = pathname === n.href || (n.href !== "/" && pathname.startsWith(n.href));
            return (
              <Link
                key={n.href}
                href={n.href}
                className={
                  "px-3 py-1.5 rounded-xl text-sm transition " +
                  (active
                    ? "bg-primary-container/30 text-primary"
                    : "text-on-surface-variant hover:text-on-surface")
                }
              >
                {n.label}
              </Link>
            );
          })}
          {authed ? (
            <button
              onClick={signOut}
              className="ml-2 px-3 py-1.5 rounded-xl text-sm text-on-surface-variant hover:text-error"
            >
              Sign out
            </button>
          ) : (
            <Link
              href="/login"
              className="ml-2 px-3 py-1.5 rounded-xl text-sm bg-primary-container/30 text-primary"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
