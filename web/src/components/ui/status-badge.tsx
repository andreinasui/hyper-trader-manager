import { type JSX } from "solid-js";
import type { Trader, RuntimeStatus } from "~/lib/types";

type AnyStatus = Trader["status"] | RuntimeStatus["state"];

export function getStatusColor(status: AnyStatus): string {
  switch (status) {
    case "running":
      return "bg-emerald-400";
    case "failed":
    case "error":
    case "not_found":
      return "bg-red-400";
    case "starting":
    case "pending":
    case "restarting":
      return "bg-amber-400";
    case "stopped":
    case "configured":
    case "unknown":
    default:
      return "bg-zinc-500";
  }
}

export function getStatusLabel(status: AnyStatus): string {
  const labels: Record<string, string> = {
    configured: "Configured",
    starting: "Starting",
    running: "Running",
    stopped: "Stopped",
    failed: "Failed",
    pending: "Pending",
    restarting: "Restarting",
    error: "Error",
    not_found: "Not found",
    unknown: "Unknown",
  };
  return labels[status] ?? String(status);
}

interface StatusDotProps {
  status: AnyStatus;
  class?: string;
}

export function StatusDot(props: StatusDotProps): JSX.Element {
  const isPulsing = () =>
    props.status === "starting" ||
    props.status === "pending" ||
    props.status === "restarting";

  return (
    <span
      class={`inline-block rounded-full flex-shrink-0 ${getStatusColor(props.status)} ${isPulsing() ? "animate-pulse" : ""} ${props.class ?? ""}`}
      style={{ width: "6px", height: "6px" }}
    />
  );
}

interface StatusIndicatorProps {
  status: AnyStatus;
  class?: string;
}

export function StatusIndicator(props: StatusIndicatorProps): JSX.Element {
  return (
    <span class={`inline-flex items-center gap-2 ${props.class ?? ""}`}>
      <StatusDot status={props.status} />
      <span class="text-sm text-zinc-400">{getStatusLabel(props.status)}</span>
    </span>
  );
}
