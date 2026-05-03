export type UpdateStatus = "idle" | "updating" | "rolled_back" | "failed";

export interface ServiceStatusEntry {
  image: string | null;
  running: boolean;
  healthy: boolean;
}

export interface ServiceStatus {
  api: ServiceStatusEntry;
  web: ServiceStatusEntry;
}

export interface UpdateStatusResponse {
  current_version: string | null;
  latest_version: string | null;
  update_available: boolean;
  last_checked: string | null;
  status: UpdateStatus;
  error_message: string | null;
  finished_at: string | null;
  configured: boolean;
  service_status: ServiceStatus | null;
}

export interface ApplyUpdateResponse {
  status: UpdateStatus;
  message: string;
}
