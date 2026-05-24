"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import {
  ArrowLeftIcon,
  GearIcon,
  SparkIcon,
  TableIcon,
  TerminalIcon,
} from "@/components/icons";
import { clearToken } from "@/lib/api";

const RAIL = [
  { href: "/", label: "Dashboard", icon: TableIcon },
  { href: "/chat", label: "Neural Engine", icon: SparkIcon },
  { href: "/settings", label: "Datasets", icon: TerminalIcon },
];

/**
 * App chrome: a thin left icon rail + the top bar, wrapping page content.
 * Both hide on the auth pages (login/register), which render bare.
 */
export function Chrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/login" || pathname === "/register") {
    return <>{children}</>;
  }

  return (
    <>
      {/* Left icon rail */}
      <aside className="flex fixed left-0 top-0 z-40 h-full w-16 flex-col items-center border-r border-outline/15 bg-surface/70 backdrop-blur-xl py-4">
        <Link
          href="/"
          aria-label="QueryMind home"
          className="grid h-9 w-9 place-items-center rounded-lg bg-primary-container/20 text-primary-container qm-glow mb-6"
        >
          <SparkIcon width={18} height={18} />
        </Link>
        <nav className="flex flex-col items-center gap-2 flex-1">
          {RAIL.map((r) => {
            const active =
              pathname === r.href ||
              (r.href !== "/" && pathname.startsWith(r.href));
            const Icon = r.icon;
            return (
              <Link
                key={r.href}
                href={r.href}
                title={r.label}
                aria-label={r.label}
                className={
                  "grid h-10 w-10 place-items-center rounded-lg transition " +
                  (active
                    ? "bg-primary-container/15 text-primary-container qm-glow"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/50")
                }
              >
                <Icon width={20} height={20} />
              </Link>
            );
          })}
        </nav>
        <Link
          href="/settings"
          title="Settings"
          aria-label="Settings"
          className="grid h-10 w-10 place-items-center rounded-lg text-on-surface-variant hover:text-on-surface transition"
        >
          <GearIcon width={20} height={20} />
        </Link>
        <button
          title="Sign out"
          aria-label="Sign out"
          onClick={() => {
            clearToken();
            router.push("/login");
          }}
          className="grid h-10 w-10 place-items-center rounded-lg text-on-surface-variant hover:text-error transition"
        >
          <ArrowLeftIcon width={20} height={20} />
        </button>
      </aside>

      {/* Content, offset for the fixed rail */}
      <div className="pl-16">{children}</div>
    </>
  );
}
