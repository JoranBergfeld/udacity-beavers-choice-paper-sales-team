import { useMemo, useRef, useState } from "react";
import { openWS } from "../api/ws";
import type { EvalReport, EvalRequestEntry, RubricDTO } from "../api/types";

// Which deterministic checks belong to which character (for the scorecards).
const CHECK_OWNER: Record<string, string> = {
  price_math: "Jim Halpert",
  discount_rule: "Jim Halpert",
  valid_item_names: "Stanley Hudson",
  no_leakage: "Michael Scott",
};

function aggregateChecks(requests: EvalRequestEntry[]) {
  const acc: Record<string, { passed: number; total: number }> = {};
  for (const r of requests)
    for (const c of r.deterministic ?? []) {
      acc[c.name] = acc[c.name] ?? { passed: 0, total: 0 };
      acc[c.name].total += 1;
      if (c.passed) acc[c.name].passed += 1;
    }
  return acc;
}

function Flag({ ok, label }: { ok: boolean; label: string }) {
  return <div className={`flag ${ok ? "ok" : "bad"}`}>{ok ? "✅" : "❌"} {label}</div>;
}

export default function PerformanceReviews() {
  const [limit, setLimit] = useState<number | null>(10);
  const [judge, setJudge] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [report, setReport] = useState<EvalReport | null>(null);
  const [entries, setEntries] = useState<EvalRequestEntry[]>([]);
  const [liveRubric, setLiveRubric] = useState<RubricDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const run = () => {
    setRunning(true);
    setProgress(0);
    setReport(null);
    setEntries([]);
    setLiveRubric(null);
    setError(null);
    const ws = openWS("/ws/eval", onMessage, (sock) =>
      sock.send(JSON.stringify({ limit, judge }))
    );
    wsRef.current = ws;
  };

  const onMessage = (m: any) => {
    if (m.type === "progress") {
      setProgress((p) => p + 1);
      if (m.entry) setEntries((prev) => [...prev, m.entry as EvalRequestEntry]);
      if (m.rubric) setLiveRubric(m.rubric as RubricDTO);
    } else if (m.type === "report") {
      setReport(m.report as EvalReport);
      setRunning(false);
      wsRef.current?.close();
    } else if (m.type === "error") {
      setError(String(m.detail ?? "The eval run hit an error."));
      setRunning(false);
      wsRef.current?.close();
    }
  };

  // Render from the final report once it arrives, otherwise from the live stream.
  const requests = report?.requests ?? entries;
  const rubric = report?.rubric ?? liveRubric;
  const checks = useMemo(() => aggregateChecks(requests), [requests]);

  const total = limit ?? 70;
  const pct = Math.min(100, Math.round((progress / total) * 100));

  return (
    <div className="container">
      <h2 className="h2">Performance Reviews 📊</h2>
      <p className="subtitle">Run the request batch, prove rubric compliance, grade the team.</p>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ alignItems: "center" }}>
          <select
            style={{ maxWidth: 140 }}
            value={limit === null ? "all" : String(limit)}
            onChange={(e) =>
              setLimit(e.target.value === "all" ? null : Number(e.target.value))
            }
          >
            <option value="10">First 10</option>
            <option value="30">First 30</option>
            <option value="all">All 70</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", width: "auto" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={judge} onChange={(e) => setJudge(e.target.checked)} />
            LLM judge
          </label>
          <div style={{ flex: 1 }} />
          <button disabled={running} onClick={run}>
            {running ? "Running…" : "▶ Run Performance Reviews"}
          </button>
        </div>
        {running && (
          <div style={{ marginTop: "0.75rem" }}>
            <div className="bar">
              <span style={{ width: `${pct}%` }} />
            </div>
            <div className="subtitle">{progress} / {total} processed</div>
          </div>
        )}
      </div>

      {error && (
        <div className="flag bad" style={{ marginBottom: "1rem" }}>
          ⚠️ {error}
        </div>
      )}

      {rubric && (
        <>
          <div className="label">
            Rubric compliance {!report && <span className="subtitle">(live)</span>}
          </div>
          <div className="row" style={{ margin: "0.4rem 0 1rem", flexWrap: "wrap" }}>
            <Flag ok={rubric.cash_change_count >= 3} label={`≥3 cash changes (${rubric.cash_change_count})`} />
            <Flag ok={rubric.fulfilled_count >= 3} label={`≥3 fulfilled (${rubric.fulfilled_count})`} />
            <Flag ok={rubric.not_all_fulfilled} label={`Not all fulfilled (${rubric.declined_count} declined)`} />
            <Flag ok={rubric.all_helpers_used} label={`All 7 helpers used`} />
          </div>

          <div className="label">Agent scorecards (deterministic checks)</div>
          <div className="row" style={{ margin: "0.4rem 0 1rem", flexWrap: "wrap" }}>
            {Object.entries(checks).map(([name, s]) => (
              <div key={name} className="card col" style={{ minWidth: 180 }}>
                <div className="aname">{CHECK_OWNER[name] ?? "Team"}</div>
                <div className="subtitle" style={{ margin: 0 }}>{name}</div>
                <div className="v" style={{ fontSize: "1.1rem" }}>
                  {s.passed}/{s.total} passed
                </div>
              </div>
            ))}
          </div>

          <div className="label">Fulfilled vs declined</div>
          <div className="card" style={{ margin: "0.4rem 0 1rem" }}>
            <div>✅ Fulfilled: {rubric.fulfilled_count}</div>
            <div className="bar" style={{ margin: "0.3rem 0" }}>
              <span
                style={{
                  width: `${(rubric.fulfilled_count /
                    Math.max(1, rubric.fulfilled_count + rubric.declined_count)) * 100}%`,
                  background: "var(--ok)",
                }}
              />
            </div>
            <div>❌ Declined: {rubric.declined_count}</div>
          </div>

          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <div className="label">Per-request</div>
            {report && (
              <a href="/api/eval/results.csv" download>⬇ Download test_results.csv</a>
            )}
          </div>
          <div className="card" style={{ marginTop: "0.4rem", maxHeight: 320, overflowY: "auto" }}>
            <table>
              <thead>
                <tr><th>#</th><th>Date</th><th>Outcome</th><th>Checks passed</th></tr>
              </thead>
              <tbody>
                {requests.map((r) => {
                  const passed = (r.deterministic ?? []).filter((c) => c.passed).length;
                  const total = (r.deterministic ?? []).length;
                  return (
                    <tr key={r.request_id}>
                      <td>{r.request_id}</td>
                      <td>{r.request_date}</td>
                      <td>{r.fulfilled ? "✅ fulfilled" : "❌ declined"}</td>
                      <td>{passed}/{total}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
