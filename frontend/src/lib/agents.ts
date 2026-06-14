export interface AgentMeta {
  id: string;
  name: string;
  emoji: string;
  role: string;
}

export const AGENTS: AgentMeta[] = [
  { id: "Michael", name: "Michael Scott", emoji: "🧑‍💼", role: "Orchestrator" },
  { id: "Dwight", name: "Dwight Schrute", emoji: "📦", role: "Inventory" },
  { id: "Jim", name: "Jim Halpert", emoji: "💼", role: "Quoting" },
  { id: "Stanley", name: "Stanley Hudson", emoji: "🧾", role: "Sales" },
  { id: "David", name: "David Wallace", emoji: "📊", role: "Advisor" },
];

export type AgentStatus = "idle" | "queued" | "working" | "done";
