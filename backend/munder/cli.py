from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from backend.munder import agents as agents_mod
from backend.munder import orchestrator
from backend.munder.eval import harness


def make_run_fn(model: Optional[Model] = None):
    """Build an async run_fn(request_text, request_date, emit) using real agents."""
    built = agents_mod.build_agents(model=model)

    async def run_fn(request_text, request_date, emit):
        return await orchestrator.run_request(
            request_text=request_text, request_date=request_date,
            built=built, model=model, emit=emit)

    return run_fn


def main(argv: Optional[List[str]] = None) -> int:
    from dotenv import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser(description="Munder Difflin headless eval")
    parser.add_argument("--sample", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", default=".")
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--test-model", action="store_true",
                        help="use pydantic-ai TestModel (no network, for smoke runs)")
    args = parser.parse_args(argv)

    model = TestModel() if args.test_model else None
    run_fn = make_run_fn(model=model)

    report = harness.run_eval(
        sample_csv=args.sample, data_dir=args.data_dir, run_fn=run_fn,
        out_dir=args.out, judge=None if args.no_judge else _default_judge(model),
        limit=args.limit,
    )

    r = report["rubric"]
    print("===== RUBRIC SUMMARY =====")
    print(f"Fulfilled: {r['fulfilled_count']}  Declined: {r['declined_count']}  "
          f"Cash changes: {r['cash_change_count']}")
    print(f"All 7 helpers used: {r['all_helpers_used']}")
    print(f"Wrote {args.out}/test_results.csv and {args.out}/eval_report.json")
    return 0


def _default_judge(model):
    from backend.munder.eval.judge import build_judge, judge_text
    judge_agent = build_judge(model=model)

    async def judge(request_text, result):
        scores = await judge_text(judge_agent, "Michael", result.reply.text)
        return {"michael": scores.model_dump()}

    return judge


if __name__ == "__main__":
    raise SystemExit(main())
