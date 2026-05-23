"use client";

import type { KPI } from "@/lib/types";

export function KPICard({ spec }: { spec: KPI }) {
  return (
    <div className="space-y-2">
      <div className="text-on-surface-variant uppercase text-xs tracking-wider">
        {spec.label}
      </div>
      <div className="flex items-baseline gap-2">
        <div className="font-mono text-3xl text-on-surface">
          {typeof spec.value === "number"
            ? spec.value.toLocaleString()
            : spec.value}
        </div>
        {spec.unit ? (
          <div className="text-on-surface-variant text-sm">{spec.unit}</div>
        ) : null}
      </div>
      {typeof spec.delta === "number" ? (
        <div
          className={
            spec.delta >= 0
              ? "text-tertiary text-sm"
              : "text-error text-sm"
          }
        >
          {spec.delta >= 0 ? "▲" : "▼"} {Math.abs(spec.delta).toFixed(1)}%
        </div>
      ) : null}
    </div>
  );
}
