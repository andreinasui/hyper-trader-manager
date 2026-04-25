import type { Trader } from "~/lib/types";

/** Relative time string from ISO timestamp */
export function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** Format uptime duration from ISO start timestamp */
export function formatUptime(startedAt: string | undefined): string {
  if (!startedAt) return "—";
  const diff = Date.now() - new Date(startedAt).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "< 1m";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

/** Semver a > b */
export function semverGt(a: string, b: string): boolean {
  const [aMaj, aMin, aPat] = a.split(".").map(Number);
  const [bMaj, bMin, bPat] = b.split(".").map(Number);
  if (aMaj !== bMaj) return aMaj > bMaj;
  if (aMin !== bMin) return aMin > bMin;
  return aPat > bPat;
}

/** Truncate wallet: 0x1234…abcd */
export function shortWallet(addr: string): string {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

/** Whether trader can be started */
export function canStart(t: Trader): boolean {
  return ["configured", "stopped", "failed"].includes(t.status);
}

/** Whether trader can be stopped */
export function canStop(t: Trader): boolean {
  return ["running", "starting"].includes(t.status);
}

/** Status border-left color class */
export function statusBorderClass(status: Trader["status"]): string {
  switch (status) {
    case "running": return "border-l-success";
    case "failed": return "border-l-error";
    case "starting": return "border-l-warning";
    default: return "border-l-border-default";
  }
}

/** Status bg tint class for rows/cards */
export function statusTintClass(status: Trader["status"]): string {
  switch (status) {
    case "running": return "bg-success/[0.03]";
    case "failed": return "bg-error/[0.05]";
    case "starting": return "bg-warning/[0.04]";
    default: return "";
  }
}
