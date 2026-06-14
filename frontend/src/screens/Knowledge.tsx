import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CatalogItem, PolicyDTO } from "../api/types";

type Tab = "catalog" | "policies" | "quotes";

export default function Knowledge() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [policy, setPolicy] = useState<PolicyDTO | null>(null);
  const [quotes, setQuotes] = useState<Record<string, unknown>[]>([]);
  const [restockQty, setRestockQty] = useState<Record<string, number>>({});
  const [saved, setSaved] = useState(false);

  const loadCatalog = () => api.catalog().then((r) => setItems(r.items));
  useEffect(() => {
    loadCatalog();
    api.policies().then(setPolicy);
    api.quotes().then((r) => setQuotes(r.quotes));
  }, []);

  const restock = async (name: string) => {
    const qty = restockQty[name] ?? 0;
    if (qty <= 0) return;
    await api.restock(name, qty);
    await loadCatalog();
  };

  const savePolicy = async () => {
    if (!policy) return;
    await api.putPolicies(policy);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="container">
      <h2 className="h2">Supply Closet 🗃️</h2>
      <p className="subtitle">Catalog & stock, business policies, and quote history.</p>

      <div className="tabs">
        {(["catalog", "policies", "quotes"] as Tab[]).map((t) => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t === "catalog" ? "Catalog & Stock" : t === "policies" ? "Policies" : "Quote History"}
          </div>
        ))}
      </div>

      {tab === "catalog" && (
        <div className="card">
          <table>
            <thead>
              <tr><th>Item</th><th>Category</th><th>Unit $</th><th>Stock</th><th>Restock</th></tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.item_name}>
                  <td>{it.item_name}</td>
                  <td>{it.category}</td>
                  <td>${it.unit_price.toFixed(2)}</td>
                  <td>{it.stock}</td>
                  <td>
                    <div className="row" style={{ gap: "0.3rem" }}>
                      <input
                        style={{ maxWidth: 80 }}
                        type="number"
                        value={restockQty[it.item_name] ?? ""}
                        onChange={(e) =>
                          setRestockQty((p) => ({ ...p, [it.item_name]: Number(e.target.value) }))
                        }
                      />
                      <button className="secondary" onClick={() => restock(it.item_name)}>+</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "policies" && policy && (
        <div className="card">
          <div className="label">Cash floor</div>
          <input
            type="number"
            style={{ maxWidth: 200 }}
            value={policy.cash_floor}
            onChange={(e) => setPolicy({ ...policy, cash_floor: Number(e.target.value) })}
          />
          <div className="label" style={{ marginTop: "1rem" }}>Discount tiers (min units → %)</div>
          <table style={{ maxWidth: 360 }}>
            <thead><tr><th>Min units</th><th>Discount %</th></tr></thead>
            <tbody>
              {policy.discount_tiers.map((t, i) => (
                <tr key={i}>
                  <td>
                    <input
                      type="number"
                      value={t.min_units}
                      onChange={(e) => {
                        const tiers = [...policy.discount_tiers];
                        tiers[i] = { ...t, min_units: Number(e.target.value) };
                        setPolicy({ ...policy, discount_tiers: tiers });
                      }}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={t.pct}
                      onChange={(e) => {
                        const tiers = [...policy.discount_tiers];
                        tiers[i] = { ...t, pct: Number(e.target.value) };
                        setPolicy({ ...policy, discount_tiers: tiers });
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: "1rem" }}>
            <button onClick={savePolicy}>Save policies</button>
            {saved && <span className="flag ok" style={{ marginLeft: "0.6rem" }}>Saved!</span>}
          </div>
        </div>
      )}

      {tab === "quotes" && (
        <div className="card" style={{ maxHeight: 460, overflowY: "auto" }}>
          {quotes.length === 0 && <p className="subtitle">No quote history yet.</p>}
          {quotes.map((q, i) => (
            <div key={i} className="msg" style={{ marginBottom: "0.4rem" }}>
              <div className="who">
                ${String(q.total_amount ?? "—")} · {String(q.job_type ?? "")} · {String(q.event_type ?? "")}
              </div>
              <div className="subtitle" style={{ margin: 0 }}>
                {String(q.quote_explanation ?? "").slice(0, 220)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
