from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from backend.munder import db
from backend.munder.events import EventCollector
from backend.munder.policies import BusinessPolicy, load_policy
from backend.munder.schemas import RunResult
from backend.munder.eval import deterministic as det

REQUIRED_HELPERS = {
    "create_transaction", "get_all_inventory", "get_stock_level",
    "get_supplier_delivery_date", "get_cash_balance",
    "generate_financial_report", "search_quote_history",
}

RunFn = Callable[..., RunResult]  # async (request_text, request_date, emit) -> RunResult


def _deterministic_checks(
    result: RunResult, policy: BusinessPolicy
) -> List[Dict[str, Any]]:
    # Same checks the live flow embeds; no_oversell uses the assessed availability that
    # the fulfillment decision was based on, so the two are always consistent.
    return [vars(c) for c in det.run_all_checks(result, policy)]


def _rubric(fulfilled: int, declined: int, cash_changes: int, helpers_used: set) -> Dict[str, Any]:
    return {
        "fulfilled_count": fulfilled,
        "declined_count": declined,
        "cash_change_count": cash_changes,
        "not_all_fulfilled": declined > 0,
        "helpers_used": sorted(helpers_used),
        "all_helpers_used": REQUIRED_HELPERS <= helpers_used,
    }


def run_eval(
    sample_csv: str,
    data_dir: str,
    run_fn: RunFn,
    out_dir: str,
    judge=None,
    policy_path: Optional[str] = None,
    limit: Optional[int] = None,
    on_request: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Run the full sample through the system; write test_results.csv + eval_report.json.

    If ``on_request`` is given, it is called after each request with that request's entry
    and the running rubric so far, which is how live progress streams to the UI."""
    import anyio

    policy = load_policy(policy_path)
    db.init_database(data_dir=data_dir, seed=137)

    sample = pd.read_csv(sample_csv)
    sample = sample.assign(
        request_date=pd.to_datetime(
            sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
    )
    sample = sample.dropna(subset=["request_date"]).sort_values("request_date")
    if limit:
        sample = sample.head(limit)

    rows: List[Dict[str, Any]] = []
    per_request: List[Dict[str, Any]] = []
    helpers_used: set = set()
    cash_change_count = 0
    fulfilled_count = 0
    declined_count = 0

    for idx, (_, row) in enumerate(sample.iterrows(), start=1):
        request_date = row["request_date"].strftime("%Y-%m-%d")
        request_text = str(row["request"])
        cash_before = db.get_cash_balance(request_date)

        collector = EventCollector()

        async def _go():
            return await run_fn(request_text, request_date, collector)

        result: RunResult = anyio.run(_go)
        result.request_id = idx

        report = db.generate_financial_report(request_date)
        cash_after = report["cash_balance"]
        if abs(cash_after - cash_before) > 1e-6:
            cash_change_count += 1
        if result.sale and result.sale.fulfilled:
            fulfilled_count += 1
        else:
            declined_count += 1
        helpers_used |= collector.helpers_used()

        rows.append({
            "request_id": idx,
            "request_date": request_date,
            "cash_balance": cash_after,
            "inventory_value": report["inventory_value"],
            "response": result.reply.text,
        })

        entry = {
            "request_id": idx,
            "request_date": request_date,
            "fulfilled": bool(result.sale and result.sale.fulfilled),
            "deterministic": _deterministic_checks(result, policy),
        }
        if judge is not None:
            entry["judge"] = anyio.run(
                lambda: judge(request_text, result))  # judge -> dict[agent]->scores
        per_request.append(entry)

        if on_request is not None:
            on_request(
                entry,
                _rubric(fulfilled_count, declined_count, cash_change_count, helpers_used),
            )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["request_id", "request_date",
                 "cash_balance", "inventory_value", "response"]).to_csv(
        out / "test_results.csv", index=False)

    rubric = _rubric(fulfilled_count, declined_count, cash_change_count, helpers_used)
    report_obj = {"rubric": rubric, "requests": per_request}
    (out / "eval_report.json").write_text(json.dumps(report_obj, indent=2))
    return report_obj
