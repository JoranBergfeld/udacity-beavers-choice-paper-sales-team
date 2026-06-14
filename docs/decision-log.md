# Decision log: Munder Difflin multi-agent system

A record of the design and engineering decisions, and *why* I made them. Newest themes
first within each section. See also: [agent-flow](agent-flow.md) and the
[reflection report](reflection-report.md).

## 1. Product & scope

- **Don't extend the starter monolith; build a themed web app on a real multi-agent
  backend.** The starter `project_starter.py` was one script. I kept its DB helper
  functions (a rubric requirement) but rebuilt around them as a clean package plus a
  FastAPI + React app, themed after *The Office* ("Munder Difflin"), with the UI as the
  entrypoint. _Why:_ the goals I had in mind (a usable front end, per-agent evaluation the 
  user can see, some personality) needed structure the starter code couldn't carry.
  I also wanted to get the experience of integrating a multi-agent system into an actual app.
- **Phased delivery.** Phase 1 was the agent core plus headless eval (rubric-complete on
  its own); Phase 2 the FastAPI layer (REST + WebSocket); Phase 3 the React UI; Phase 4
  polish. _Why:_ Phase 1 alone passes the rubric, so the submission was safe even if the
  later phases ran long.

## 2. Architecture & stack

- **pydantic-ai** as the agent framework. _Why:_ typed agents with first-class structured
  outputs (clean data for the UI and the evaluator), multi-provider support, and a tidy
  orchestrator/worker pattern.
- **FastAPI backend + React/Vite (TypeScript) frontend**, two processes, talking over REST
  plus two WebSocket channels. _Why:_ the frameworks are Python, but the live "watch the
  agents work" view and the eval dashboard wanted a real frontend, and WebSockets stream
  agent events and eval progress naturally.
- **The rubric-critical path runs headless** via `backend/munder/cli.py` with no dependence
  on the web app; the UI's "Run eval" calls the same harness. _Why:_ the graded artifact
  (`test_results.csv`) has to be reproducible without the frontend.
- **Charts are hand-rolled (CSS/SVG), with native `fetch`/`WebSocket`.** _Why:_ keeps the
  frontend dependency footprint tiny.

## 3. Agent design

- **Five agents (the rubric max), with distinct, non-overlapping roles:** Michael
  (orchestrator), Dwight (inventory), Jim (quoting), Stanley (sales/fulfillment), and
  David Wallace (business advisor, the "stand-out" agent). Their tools collectively use all
  7 starter helper functions.
- **Michael orchestrates** (I picked him over Pam-as-reception). "World's Best Boss who
  delegates" fit the orchestration role and the theme.
- **Delegation-then-synthesis flow** instead of free-form agent chat: Michael emits a
  structured plan, a thin Python orchestrator runs the needed workers, each returns a typed
  result, and Michael synthesizes the customer reply. _Why:_ debuggable, typed hand-offs;
  the UI and evaluator read structured data instead of scraped prose.
- **Personas are code-managed, not UI-editable.** _Why:_ they're behavior and guardrails,
  not business data. (Knowledge management covers catalog, policies, and quote history
  instead.)
- **Stronger persona prompts after switching to gpt-5.4.** gpt-5.4 is more neutral than
  gpt-4o, so I added explicit voice/catchphrase direction to keep the characters
  recognizable.

## 4. Determinism (the recurring theme)

The biggest shift over the project: move the *decisions and numbers* out of the LLM and
into deterministic code, and let the agents parse language and narrate in character. Real
models kept failing the eval until I did this.

- **Deterministic pricing** (`price_order`): line totals come from the catalog unit price,
  and the bulk-discount tier is applied in code. _Why:_ the model produced wrong, ad-hoc
  discounts (e.g. a "1000%" discount from a fraction/percent mix-up), and the `price_math`
  and `discount_rule` checks failed.
- **Catalog canonicalization of item names** (`canonical_item_name`: exact, then
  case-insensitive, then fuzzy) and **catalog-constrained parsing** (Michael picks the
  closest catalog name). _Why:_ `valid_item_names` was 0/10; the model paraphrased ("A4
  glossy paper" vs. catalog "Glossy paper").
- **Parse once into a shared `ParsedOrder`** (Michael), used by all workers, with duplicate
  items merged. _Why:_ when each agent re-parsed on its own they disagreed on quantities;
  merging fixed per-line vs. aggregate oversell.
- **Deterministic inventory assessment and fulfillment decision.** _Why:_ consistent,
  reproducible fulfilled/declined outcomes that match the eval's `no_oversell` check by
  construction.
- **Delegation derived from the order, not the model's flags** (any real order runs the
  full pipeline). _Why:_ a too-aggressive "omit items with no match" parse instruction once
  produced empty orders and an all-declined run.
- **Insufficient stock is the only decline reason** (I ship from stock; supplier lead time
  is reported, not a blocker). _Why:_ delivery-deadline declines made the system too
  conservative, and this matches the rubric's intended "insufficient stock" reason.
- **Auto-restock when affordable** (buy the shortfall if cash stays above the floor).
  _Why:_ the seed stocks only ~40% of the catalog, so most requests declined; restocking
  turns affordable shortfalls into sales while the genuinely unaffordable ones still
  decline.
- **Deterministic helper coverage:** the orchestrator invokes (and emits events for) all 7
  helpers regardless of which tools the LLM decides to call. _Why:_ "all 7 helpers used"
  can't hang on model-specific tool-calling behavior.

## 5. Evaluation

- **Two layers:** the rubric financial sim (`test_results.csv` plus auto-checked
  thresholds) and a per-agent quality review (deterministic checks plus LLM-as-judge).
- **Deterministic + LLM-judge** rather than one or the other. _Why:_ hard correctness
  guarantees, plus nuance on tone, transparency, and personality.
- **Evaluation embedded in the live flow**, not just the batch dashboard: each Reception
  request runs the deterministic checks and the judge and shows a quality panel.
- **Performance Reviews stream per request** (the table, tallies, and rubric flags fill in
  live) instead of appearing all at once. _Why:_ a real WebSocket should show progress; a
  long "all 70" run is otherwise just a spinner.

## 6. LLM provider & configuration

- **Provider-agnostic config, defaulting to the Udacity/Vocareum proxy, with Azure AI
  Foundry available via `.env`.** `MUNDER_PROVIDER=openai|azure` picks the path. _Why:_
  repeated test runs drained the Udacity budget, and Azure lets me use a separate budget
  with no code changes.
- **Demo mode (TestModel) when no API key is set** for the active provider. _Why:_ the app
  stays fully usable without credentials, and the test suite never hits a live endpoint.
- **The UI model selector drives the real model** (`current_model` builds from config).
- **Azure as backup:** I ran out of budget during development. I used a `gpt-5.4` 
  deployment in Azure I still had deployed. That way I could continue development.
  Note that I have created the initial version of this app with the provided model,
  but later moved to the `gpt-5.4` model in Azure.

## 7. Engineering & process

- **Work stays uncommitted on `main`** (no commits, branches, or push) per my standing
  preference; Phases 2 and 3 were built inline rather than via committing subagents.
- **Removed the `starter/` folder.** The CSVs live in `backend/munder/data/` now, and the
  product catalog moved out of `db.py` into `catalog.py` (data separated from logic). The
  starter helper functions were kept (rubric provenance).
- **Tests are hermetic:** the API test fixture neutralizes *every* provider key, so a
  developer's real `.env` (Azure, say) can never make the suite call a live endpoint.

## 8. Notable fixes & learnings

- **Load `.env` in the API app.** Config read the environment but nothing loaded `.env`, so
  the app sat in demo mode even with a key present.
- **Sanitize non-JSON floats** (`NaN`/`inf` to `null`) in API responses. The seed's
  opening-balance row produced `NaN` in `top_selling_products` once real sales existed, and
  Starlette's encoder rejects that.
- **WebSocket resilience.** Surface orchestrator/LLM errors to the client as an `error`
  message and tolerate client disconnects, instead of crashing the handler and hiding the
  real error.
- **Per-request eval resilience.** One failing request must not take down the whole batch.
- **Quiet the noise.** Removed a leftover starter debug `print`, and rewrote
  chained-DataFrame assignments with `.assign()` to stop the pandas `FutureWarning` spam.
