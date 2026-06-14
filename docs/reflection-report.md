# Munder Difflin: reflection report

## 1. Agent workflow & architecture

It's a five-agent team built on **pydantic-ai**, with a FastAPI + React app on top. The
agents and their tools are drawn out in `docs/agent-flow.md`.

The roles don't overlap:

- **Michael Scott (Orchestrator).** Takes the customer request, turns it into a structured
  `DelegationPlan` (which of inventory / quoting / sales are needed), and at the end writes
  the customer-facing reply. Tool: `generate_financial_report`.
- **Dwight Schrute (Inventory).** Checks stock and recommends reorders. Tools:
  `get_all_inventory`, `get_stock_level`, `get_supplier_delivery_date`,
  `create_transaction` (restock).
- **Jim Halpert (Quoting).** Picks line items and quantities, looks at quote history, and
  explains the pricing. Tools: `search_quote_history`, `get_stock_level`.
- **Stanley Hudson (Sales / fulfillment).** Closes a sale only when stock, cash, and
  timeline all allow it, and records it. Tools: `create_transaction` (sale),
  `get_cash_balance`, `get_supplier_delivery_date`.
- **David Wallace (Business advisor, the stand-out agent).** Reviews the financial state
  and makes recommendations. Tools: `generate_financial_report`, `get_cash_balance`.

Between them the tools cover all seven required helper functions, and the eval harness
asserts at runtime that each one actually got called during a full run.

**Why this design.** I went with a delegation-then-synthesis flow instead of letting the
agents free-chat at each other. Michael emits an explicit, typed delegation plan; a thin
Python orchestrator runs only the workers that are needed, in order; each worker returns a
structured pydantic output; and Michael writes the final reply from those outputs. A few
reasons:

The typed hand-offs make the thing debuggable, and they let the UI and the evaluator read
structured data instead of scraping prose. The other half is the split of labor: the model
is good at choosing items, quantities, and writing rationale, and bad at exact arithmetic
and exact catalog names. So pricing and item-name resolution are deterministic in the
orchestrator (`_finalize_quote` plus `canonical_item_name`). The catalog is the source of
truth for unit prices and names, and the bulk-discount tiers are applied in code. The LLM
keeps selection and explanation. There's also a transparency guardrail: a shared persona
rule forbids leaking internal info (margins, internal errors, PII) to the customer, and a
deterministic scan checks that nothing slipped through.

## 2. Evaluation results

Evaluation runs the full `quote_requests_sample.csv` through the system and writes
`test_results.csv` (`request_id, request_date, cash_balance, inventory_value, response`)
plus a richer `eval_report.json`. Two layers: the rubric financial sim, and a per-agent
quality review (deterministic checks plus an optional LLM judge). A real-model run is
included at [`../test_results.csv`](../test_results.csv) in the repo root.

Rubric compliance, from a representative run:

- At least 3 requests changed the cash balance. Observed: 10. Pass.
- At least 3 requests fulfilled. Observed: 3. Pass.
- Not everything fulfilled. 7 declined, with reasons (not enough stock from the seed-137
  inventory, or delivery slipping past the requested deadline). Pass.
- All 7 helper functions used. Pass.

What went well:

- **Declines that make sense and explain themselves.** Stanley turned down orders he
  couldn't fulfill on time or in stock ("delivery date is after next week") instead of
  overselling. That's the cautious behavior the business actually wants, and it's why "not
  all fulfilled" happens on its own rather than being faked.
- **No information leakage.** `no_leakage` passed 10/10. Customer replies never exposed
  margins or internal errors.
- **Consistent quote arithmetic.** `price_math` passed 8/8.

What the eval caught, and what I did about it:

- **Discount adherence** started at 2/8. The model was making up discount percentages, and
  at one point reported a discount of `10` meaning 1000%. I fixed it by applying the
  documented bulk-discount tiers deterministically in `_finalize_quote`.
- **Item-name validity** started at 0/8. The model kept paraphrasing product names ("A4
  glossy paper" instead of the catalog's "Glossy paper"). `canonical_item_name` now maps
  free-text names to the exact catalog entry (exact, then case-insensitive, then fuzzy) for
  quotes, stock checks, sales, and restocks. That also killed a sneakier bug, where a
  "fulfilled" sale could record a phantom item and never decrement the real inventory.

There's also a no-oversell check computed per fulfilled request in the eval report. After
these fixes, a fresh run should land `discount_rule` and `valid_item_names` near perfect.

## 3. What I'd improve next

1. **Negotiation / counter-offer loop.** When Stanley declines on timeline or stock, have
   the system propose an alternative (partial fulfillment now plus a backorder, or a
   nearby in-stock substitute) instead of a flat no. That would turn some of the 7 declines
   into sales without lying about the constraints.

2. **Actually run the reorders.** Right now Dwight recommends reorders and David advises,
   but nobody pulls the trigger. I'd wire these into automatic `create_transaction`
   restocks when stock drops below the minimum and cash allows it (respecting the cash
   floor). The eval already tracks inventory value over time, so the effect on fulfillment
   rate and assets would be easy to measure.

3. **(Bonus) One policy source.** The discount/reorder/cash-floor policy is editable in the
   UI, but the eval check still uses the default policy. Wiring both to the same
   `policies.json` would let business users tune behavior and see it move the scores.
