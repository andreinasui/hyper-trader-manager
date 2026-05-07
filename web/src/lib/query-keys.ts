export const traderKeys = {
  all: ["traders"] as const,
  lists: () => [...traderKeys.all, "list"] as const,
  detail: (id: string) => [...traderKeys.all, "detail", id] as const,
  logs: (id: string, since?: string, until?: string) =>
    [...traderKeys.detail(id), "logs", since ?? null, until ?? null] as const,
  status: (id: string) => [...traderKeys.detail(id), "status"] as const,
  archives: (id: string) => [...traderKeys.detail(id), "archives"] as const,
};

export const userKeys = {
  all: ["users"] as const,
  me: () => [...userKeys.all, "me"] as const,
};

export const adminKeys = {
  all: ["admin"] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
  users: () => [...adminKeys.all, "users"] as const,
  traders: () => [...adminKeys.all, "traders"] as const,
};

export const setupKeys = {
  all: ["setup"] as const,
  status: () => [...setupKeys.all, "status"] as const,
  ssl: () => [...setupKeys.all, "ssl"] as const,
};

export const imageKeys = {
  all: ["images"] as const,
  versions: () => [...imageKeys.all, "versions"] as const,
};

export const updateKeys = {
  all: ["updates"] as const,
  status: () => [...updateKeys.all, "status"] as const,
};
