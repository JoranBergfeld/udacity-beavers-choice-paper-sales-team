import type { AgentMeta, AgentStatus } from "../lib/agents";

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "idle",
  queued: "queued",
  working: "working",
  done: "done",
};

export default function AgentBadge({
  agent,
  status,
  tool,
}: {
  agent: AgentMeta;
  status: AgentStatus;
  tool?: string;
}) {
  return (
    <div className={`agent ${status}`}>
      <div className="emoji">{agent.emoji}</div>
      <div className="aname">{agent.name}</div>
      <div className="arole">{agent.role}</div>
      <div className="astatus">
        <span className={`dot ${status}`} />
        {STATUS_LABEL[status]}
        {status === "working" && tool ? ` · ${tool}` : ""}
      </div>
    </div>
  );
}
