import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { AGENTS, type AgentStatus } from "../lib/agents";
import AgentBadge from "../components/AgentBadge";
import Stat from "../components/Stat";
import { openWS } from "../api/ws";
import { api } from "../api/client";
import type {
  CheckResult,
  FinancialReport,
  JudgeScores,
  RunEvent,
  RunResult,
} from "../api/types";

type StatusMap = Record<string, AgentStatus>;
const allIdle = (): StatusMap =>
  Object.fromEntries(AGENTS.map((a) => [a.id, "idle"])) as StatusMap;

const EXAMPLES = [
  "I need 500 reams of A4 paper and 200 of cardstock, delivered by April 20.",
  "Quote me 50 packs of paper plates and 100 paper cups for an office party.",
  "We need 2000 sheets of glossy paper for flyers next week.",
];

export default function Reception() {
  const [text, setText] = useState(EXAMPLES[0]);
  const [date, setDate] = useState("2025-04-01");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [statuses, setStatuses] = useState<StatusMap>(allIdle());
  const [tools, setTools] = useState<Record<string, string>>({});
  const [result, setResult] = useState<RunResult | null>(null);
  const [fin, setFin] = useState<FinancialReport | null>(null);
  const [evalData, setEvalData] = useState<
    { checks: CheckResult[]; judge: JudgeScores | null } | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Show the current books immediately, before any request is sent.
  useEffect(() => {
    api.financials().then(setFin).catch(() => {});
  }, []);

  const send = () => {
    setRunning(true);
    setEvents([]);
    setResult(null);
    setError(null);
    setEvalData(null);
    setStatuses(allIdle());
    setTools({});
    const ws = openWS("/ws/reception", onMessage, (sock) =>
      sock.send(JSON.stringify({ request_text: text, request_date: date }))
    );
    wsRef.current = ws;
  };

  const onMessage = (m: any) => {
    if (m.type === "event") {
      const e: RunEvent = m.event;
      setEvents((prev) => [...prev, e]);
      if (e.kind === "agent_started" && e.agent)
        setStatuses((p) => ({ ...p, [e.agent!]: "working" }));
      if (e.kind === "tool_call" && e.agent && e.tool)
        setTools((p) => ({ ...p, [e.agent!]: e.tool! }));
      if (e.kind === "handoff" && e.data && typeof e.data.to === "string")
        setStatuses((p) => ({ ...p, [e.data!.to as string]: "queued" }));
      if (e.kind === "run_complete")
        setStatuses((p) =>
          Object.fromEntries(
            Object.entries(p).map(([k, v]) => [k, v === "idle" ? "idle" : "done"])
          ) as StatusMap
        );
    } else if (m.type === "eval") {
      setEvalData({ checks: m.checks ?? [], judge: m.judge ?? null });
    } else if (m.type === "result") {
      setResult(m.result as RunResult);
      setRunning(false);
      api.financials().then(setFin);
      wsRef.current?.close();
    } else if (m.type === "error") {
      setError(String(m.detail ?? "The team hit an error."));
      setRunning(false);
      setStatuses(allIdle());
      wsRef.current?.close();
    }
  };

  return (
    <div className="container">
      <h2 className="h2">Reception — Live Request 🏢💬</h2>
      <p className="subtitle">Send a request to the team and watch them work it.</p>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="label">Customer request</div>
        <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        <div className="chips" style={{ margin: "0.5rem 0" }}>
          {EXAMPLES.map((ex) => (
            <span key={ex} className="chip" onClick={() => setText(ex)}>
              {ex.slice(0, 38)}…
            </span>
          ))}
        </div>
        <div className="row" style={{ alignItems: "center" }}>
          <div style={{ maxWidth: 180 }}>
            <div className="label">Request date</div>
            <input value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div style={{ flex: 1 }} />
          <button disabled={running} onClick={send}>
            {running ? "Working…" : "Send to the team"}
          </button>
        </div>
      </div>

      {error && (
        <div className="flag bad" style={{ marginBottom: "1rem" }}>
          ⚠️ {error}
        </div>
      )}

      <div className="label">The Floor</div>
      <div className="floor" style={{ margin: "0.4rem 0 1rem" }}>
        {AGENTS.map((a) => (
          <AgentBadge key={a.id} agent={a} status={statuses[a.id]} tool={tools[a.id]} />
        ))}
      </div>

      <div className="row">
        <div className="col" style={{ flex: 2 }}>
          <div className="label">The Debate</div>
          <div className="chat" style={{ marginTop: "0.4rem" }}>
            {events
              .filter((e) => ["agent_message", "tool_call", "handoff"].includes(e.kind))
              .map((e, i) => (
                <div key={i} className="msg">
                  <div className="who">
                    {e.agent ?? "—"}
                    {e.kind === "handoff" && e.data
                      ? ` → ${String(e.data.to)}`
                      : ""}
                  </div>
                  {e.message && <div>{e.message}</div>}
                  {e.kind === "tool_call" && (
                    <span className="toolchip">
                      {e.tool} → {e.helper}
                    </span>
                  )}
                </div>
              ))}
            {!events.length && <p className="subtitle">No activity yet.</p>}
          </div>
        </div>

        <div className="col">
          <div className="label">The Books</div>
          <div className="grid" style={{ marginTop: "0.4rem" }}>
            <Stat
              k="Cash balance"
              v={fin ? `$${fin.cash_balance.toFixed(2)}` : "—"}
            />
            <Stat
              k="Inventory value"
              v={fin ? `$${fin.inventory_value.toFixed(2)}` : "—"}
            />
          </div>

          <div className="label" style={{ marginTop: "1rem" }}>
            Final reply
          </div>
          <div className="card" style={{ marginTop: "0.4rem" }}>
            {result ? (
              <>
                <div className="markdown">
                  <ReactMarkdown>{result.reply.text}</ReactMarkdown>
                </div>
                {result.quote && (
                  <p className="subtitle">
                    Total ${result.quote.total.toFixed(2)} ·{" "}
                    {(result.quote.discount_pct * 100).toFixed(0)}% discount
                  </p>
                )}
                <button
                  className="secondary"
                  onClick={() => navigator.clipboard.writeText(result.reply.text)}
                >
                  Copy reply
                </button>
              </>
            ) : (
              <p className="subtitle">The team's reply will appear here.</p>
            )}
          </div>

          {evalData && (
            <>
              <div className="label" style={{ marginTop: "1rem" }}>
                Quality checks
              </div>
              <div className="card" style={{ marginTop: "0.4rem" }}>
                {evalData.checks.length === 0 && (
                  <p className="subtitle" style={{ margin: 0 }}>No checks applied.</p>
                )}
                {evalData.checks.map((c, i) => (
                  <div key={i} style={{ fontSize: "0.82rem" }}>
                    {c.passed ? "✅" : "❌"} {c.name}
                  </div>
                ))}
                {evalData.judge && (
                  <div style={{ marginTop: "0.6rem", fontSize: "0.82rem" }}>
                    <div className="label">Judge (1–5)</div>
                    clarity {evalData.judge.clarity} · transparency{" "}
                    {evalData.judge.transparency} · personality{" "}
                    {evalData.judge.personality} · persuasiveness{" "}
                    {evalData.judge.persuasiveness}
                    <div className="subtitle" style={{ margin: "0.25rem 0 0" }}>
                      {evalData.judge.rationale}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
