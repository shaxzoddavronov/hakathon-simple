/**
 * Client-side unique id for React keys / optimistic message ids.
 *
 * `crypto.randomUUID()` only exists in a *secure context* (HTTPS or
 * localhost). Served over plain http on a server IP it's undefined and
 * throws, so fall back to getRandomValues, then to a time+random string.
 * These ids aren't security-sensitive, so RFC-exact v4 bits don't matter.
 */
export function uid(): string {
  const c = typeof crypto !== "undefined" ? crypto : undefined;
  if (c && typeof c.randomUUID === "function") {
    return c.randomUUID();
  }
  if (c && typeof c.getRandomValues === "function") {
    const h = Array.from(c.getRandomValues(new Uint8Array(16)), (x) =>
      x.toString(16).padStart(2, "0"),
    ).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  }
  return `id-${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}
