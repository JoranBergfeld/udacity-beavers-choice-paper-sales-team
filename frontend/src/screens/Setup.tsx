import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ConfigDTO, FinancialReport } from "../api/types";

const STEP_NAMES = ["Welcome", "Connect", "Seed", "Review", "Ready"];

export default function Setup({ onSeeded }: { onSeeded: () => void }) {
  const [step, setStep] = useState(0);
  const [config, setConfig] = useState<ConfigDTO | null>(null);
  const [conn, setConn] = useState<string>("");
  const [report, setReport] = useState<FinancialReport | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    api.getConfig().then(setConfig);
  }, []);

  const test = async () => {
    const r = await api.testConnection();
    setConn(r.demo_mode ? "Demo mode — using TestModel (no key needed)." : r.ok ? "Connected!" : `Failed: ${r.detail}`);
  };

  const saveModel = async () => {
    if (!config) return;
    const c = await api.putConfig({ model: config.model });
    setConfig(c);
    setConn(`Saved model: ${c.model}`);
  };

  const seed = async () => {
    await api.seed();
    setReport(await api.financials());
    onSeeded();
  };

  return (
    <div className="container">
      <h2 className="h2">Welcome to Munder Difflin 🏢</h2>
      <p className="subtitle">Let's get the World's Best Boss and his team ready.</p>

      <div className="steps">
        {STEP_NAMES.map((n, i) => (
          <div key={n} className={`step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>
            {i + 1}. {n}
          </div>
        ))}
      </div>

      <div className="card">
        {step === 0 && (
          <div>
            <p>
              This little app is the front desk to a five-agent paper company. Michael
              orchestrates; Dwight, Jim and Stanley do the work; David Wallace keeps an eye
              on the books. Let's set things up.
            </p>
            <button onClick={() => setStep(1)}>Start</button>
          </div>
        )}

        {step === 1 && config && (
          <div>
            <div className="label">Connect</div>
            <div className="label" style={{ marginTop: "0.5rem" }}>Model</div>
            <input
              style={{ maxWidth: 280 }}
              value={config.model}
              onChange={(e) => setConfig({ ...config, model: e.target.value })}
            />
            <p className="subtitle" style={{ margin: "0.3rem 0 0" }}>
              Provider: <b>{config.provider}</b> · Endpoint: <code>{config.base_url}</code>
            </p>
            {config.demo_mode && (
              <p className="flag bad">
                No API key found — the app runs in <b>demo mode</b> (TestModel). Set
                UDACITY_OPENAI_API_KEY in the environment for real responses.
              </p>
            )}
            <div className="row">
              <button onClick={saveModel}>Save model</button>
              <button className="secondary" onClick={test}>Test connection</button>
              <button className="secondary" onClick={() => setStep(2)}>Next</button>
            </div>
            {conn && <p style={{ marginTop: "0.5rem" }}>{conn}</p>}
          </div>
        )}

        {step === 2 && (
          <div>
            <div className="label">Seed the database</div>
            <p>Start the company with $50,000 cash and a seeded inventory (seed 137).</p>
            <div className="row">
              <button onClick={seed}>Initialize / reset</button>
              <button className="secondary" disabled={!report} onClick={() => setStep(3)}>Next</button>
            </div>
            {report && (
              <p className="flag ok" style={{ marginTop: "0.5rem" }}>
                Seeded! Cash ${report.cash_balance.toFixed(2)} · Inventory ${report.inventory_value.toFixed(2)}
              </p>
            )}
          </div>
        )}

        {step === 3 && (
          <div>
            <div className="label">Review the knowledge base</div>
            <p>
              Your catalog, stock, business policies and quote history live in the Supply
              Closet — you can tweak them anytime. Take a peek after setup.
            </p>
            <button onClick={() => setStep(4)}>Next</button>
          </div>
        )}

        {step === 4 && (
          <div>
            <div className="label">Ready</div>
            <p>That's what she said. The team is ready to take a customer request.</p>
            <button onClick={() => nav("/")}>Go to Reception</button>
          </div>
        )}
      </div>
    </div>
  );
}
