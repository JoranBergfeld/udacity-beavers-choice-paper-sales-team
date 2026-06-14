# Munder Difflin: a multi-agent paper company

A fake paper company, Munder Difflin, run by five AI agents who think they're characters
from *The Office*. Hand it a customer request and it works the whole thing: checks
inventory, builds a quote with bulk discounts, then closes or declines the sale. There's a
small web app on the front so you can watch it happen.

The trick that holds it together: the agents parse the request and narrate in character,
but the actual decisions and numbers (what's in stock, the price, whether to fulfill) run
in plain Python. So the characters can be as chaotic as they like and the math still comes
out right, on any model.

## The team

| Agent | Character | Responsibility |
|---|---|---|
| Orchestrator | **Michael Scott** | Parses the request, delegates, writes the customer reply |
| Inventory | **Dwight Schrute** | Stock checks & reorder recommendations |
| Quoting | **Jim Halpert** | Builds the quote, applies bulk discounts |
| Sales / fulfillment | **Stanley Hudson** | Closes or declines the order; records the sale |
| Business advisor | **David Wallace** | Reviews finances, flags issues (stand-out feature) |

Between them, their tools call all seven starter helper functions (`create_transaction`,
`get_all_inventory`, `get_stock_level`, `get_supplier_delivery_date`, `get_cash_balance`,
`generate_financial_report`, `search_quote_history`).

## What's in the box

- `backend/munder/`: the agent system (pydantic-ai), the deterministic decision engine,
  the headless eval harness, and the starter DB helpers plus product catalog.
- `backend/api/`: a FastAPI app exposing config/setup, knowledge, and financials over REST,
  plus two WebSocket channels (live single-request processing and streaming evaluation).
- `frontend/`: a React/Vite app. Setup wizard, Reception (live floor map, agent debate,
  financials), Performance Reviews (eval dashboard), and the Supply Closet (catalog,
  policies, quote history).
- `tests/`: the backend test suite. Runs fully offline via pydantic-ai's `TestModel`.
- `docs/`: design docs (listed below).

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12) and Node 18+.

```bash
# 1. Backend deps + a Python 3.12 env
uv venv --python 3.12
uv sync --all-groups

# 2. Configure providers (optional; runs in demo mode without a key)
cp .env.example .env   # then fill in a key; see "Configuration" below

# 3. Run the API (http://localhost:8000)
uv run uvicorn backend.api.app:app --port 8000

# 4. Run the UI (http://localhost:5173) in another terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The first run lands on the Setup wizard, then Reception.

**Demo mode:** no API key? The app falls back to pydantic-ai's `TestModel`. No network, no
cost, so you can click through everything. Set a key when you want real responses.

## Configuration

Copy `.env.example` to `.env`. Pick a provider with `MUNDER_PROVIDER`:

**OpenAI-compatible (default; Udacity/Vocareum proxy):**
```bash
MUNDER_PROVIDER=openai
UDACITY_OPENAI_API_KEY=your_key
MUNDER_MODEL=gpt-4o
# UDACITY_BASE_URL=https://openai.vocareum.com/v1   # default
```

**Azure AI Foundry / Azure OpenAI:**
```bash
MUNDER_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name   # the deployment name = the model id on Azure
```

Restart the API after changing `.env`.

## Evaluation (the rubric artifact)

A sample real-model run lives at [`test_results.csv`](test_results.csv) in the repo root:
`request_id, request_date, cash_balance, inventory_value, response` for the full
`quote_requests_sample.csv`.

To regenerate it, run the whole sample through the system. That produces `test_results.csv`
and `eval_report.json`:

- **From the UI:** Performance Reviews, pick a size, then "Run Performance Reviews". It
  updates per request and downloads `test_results.csv`.
- **Headless:**
  ```bash
  uv run python -m backend.munder.cli \
    --sample backend/munder/data/quote_requests_sample.csv \
    --data-dir backend/munder/data --out .
  # add --test-model to run offline (demo), --limit N to cap, --no-judge to skip the LLM judge
  ```

Every request also gets evaluated live in Reception (deterministic checks plus an LLM
judge).

## Tests

```bash
uv run pytest -q     # offline; uses TestModel, never calls a live endpoint
```

## Documentation

- [Agent flow diagram](docs/agent-flow.md): the five agents, their tools, and which helper
  function each tool uses (Mermaid).
- [Decision log](docs/decision-log.md): the design and engineering decisions, and why I
  made them.
- [Reflection report](docs/reflection-report.md): how the architecture works, the
  evaluation results, and what I'd improve next.
- The design spec and implementation plans live under `docs/superpowers/`.
