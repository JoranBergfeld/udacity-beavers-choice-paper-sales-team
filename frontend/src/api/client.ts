import type {
  CatalogItem,
  ConfigDTO,
  FinancialReport,
  PolicyDTO,
} from "./types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const api = {
  getConfig: () => fetch("/api/config").then((r) => j<ConfigDTO>(r)),
  putConfig: (b: Partial<ConfigDTO>) =>
    fetch("/api/config", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(b),
    }).then((r) => j<ConfigDTO>(r)),
  status: () =>
    fetch("/api/status").then((r) =>
      j<{ db_seeded: boolean; demo_mode: boolean }>(r)
    ),
  seed: () =>
    fetch("/api/seed", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ reset: true }),
    }).then((r) => j<{ db_seeded: boolean }>(r)),
  testConnection: () =>
    fetch("/api/test-connection", { method: "POST" }).then((r) =>
      j<{ ok: boolean; demo_mode: boolean; detail?: string }>(r)
    ),
  catalog: () =>
    fetch("/api/catalog").then((r) => j<{ items: CatalogItem[] }>(r)),
  policies: () => fetch("/api/policies").then((r) => j<PolicyDTO>(r)),
  putPolicies: (b: PolicyDTO) =>
    fetch("/api/policies", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(b),
    }).then((r) => j<{ ok: boolean }>(r)),
  quotes: () =>
    fetch("/api/quotes").then((r) =>
      j<{ quotes: Record<string, unknown>[] }>(r)
    ),
  restock: (item_name: string, quantity: number) =>
    fetch("/api/restock", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ item_name, quantity }),
    }).then((r) => j<{ ok: boolean }>(r)),
  financials: () => fetch("/api/financials").then((r) => j<FinancialReport>(r)),
};
