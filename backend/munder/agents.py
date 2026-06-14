from __future__ import annotations

import os
from typing import Dict, List, Optional

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend.munder import tools
from backend.munder.personas import PERSONAS
from backend.munder.schemas import (
    Intake, InventoryAssessment, Quote, SaleResult, AdvisorNote,
)
from backend.munder.tools import Deps


def build_model(model_name: Optional[str] = None, base_url: Optional[str] = None) -> Model:
    """Build the LLM model for the configured provider.

    Provider is selected by the ``MUNDER_PROVIDER`` env var:
      - ``openai`` (default): an OpenAI-compatible endpoint (the Udacity/Vocareum proxy
        by default), using UDACITY_BASE_URL + UDACITY_OPENAI_API_KEY + MUNDER_MODEL.
      - ``azure``: Azure AI Foundry / Azure OpenAI, using AZURE_OPENAI_ENDPOINT +
        AZURE_OPENAI_API_KEY + AZURE_OPENAI_API_VERSION + AZURE_OPENAI_DEPLOYMENT.

    Explicit ``model_name``/``base_url`` args (e.g. from the UI config) win over the env
    defaults. API keys always come from the environment.
    """
    provider = os.environ.get("MUNDER_PROVIDER", "openai").lower()

    if provider == "azure":
        from pydantic_ai.providers.azure import AzureProvider

        deployment = (
            model_name
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            or os.environ.get("MUNDER_MODEL", "gpt-4o")
        )
        return OpenAIModel(
            deployment,
            provider=AzureProvider(
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
                api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            ),
        )

    return OpenAIModel(
        model_name or os.environ.get("MUNDER_MODEL", "gpt-4o"),
        provider=OpenAIProvider(
            base_url=base_url
            or os.environ.get("UDACITY_BASE_URL", "https://openai.vocareum.com/v1"),
            api_key=os.environ.get("UDACITY_OPENAI_API_KEY", "missing"),
        ),
    )


def build_agents(model: Optional[Model] = None) -> Dict[str, Agent]:
    """Construct the five agents. Pass a TestModel/FunctionModel for tests."""
    model = model or build_model()

    # ---- Michael Scott: Orchestrator (parses the order + decides delegation) ----
    michael = Agent(
        model, deps_type=Deps, output_type=Intake,
        system_prompt=PERSONAS["michael"]["prompt"],
    )

    @michael.tool
    def financial_report_michael(ctx: RunContext[Deps]) -> Dict:
        """Full financial report as of the request date."""
        return tools.financial_report(ctx)

    # ---- Dwight Schrute: Inventory ----
    dwight = Agent(
        model, deps_type=Deps, output_type=InventoryAssessment,
        system_prompt=PERSONAS["dwight"]["prompt"],
    )

    @dwight.tool
    def check_all_inventory(ctx: RunContext[Deps]) -> Dict[str, int]:
        """Snapshot of all in-stock items as of the request date."""
        return tools.check_all_inventory(ctx)

    @dwight.tool
    def check_stock(ctx: RunContext[Deps], item_name: str) -> int:
        """Net stock for a single item as of the request date."""
        return tools.check_stock(ctx, item_name)

    @dwight.tool
    def delivery_estimate(ctx: RunContext[Deps], quantity: int) -> str:
        """Supplier delivery date for a quantity, based on the request date."""
        return tools.delivery_estimate(ctx, quantity)

    @dwight.tool
    def restock_item(ctx: RunContext[Deps], item_name: str, quantity: int, unit_price: float) -> int:
        """Place a stock order (reorder) for an item; returns the transaction id."""
        return tools.restock_item(ctx, item_name, quantity, unit_price)

    @dwight.tool
    def order_inventory(ctx: RunContext[Deps]) -> Dict:
        """Authoritative availability for the whole parsed order. Report this verbatim."""
        return tools.order_inventory(ctx)

    # ---- Jim Halpert: Quoting ----
    jim = Agent(
        model, deps_type=Deps, output_type=Quote,
        system_prompt=PERSONAS["jim"]["prompt"],
    )

    @jim.tool
    def search_quotes(ctx: RunContext[Deps], search_terms: List[str]) -> List[Dict]:
        """Search historical quotes for pricing precedent."""
        return tools.search_quotes(ctx, search_terms)

    @jim.tool
    def check_stock_jim(ctx: RunContext[Deps], item_name: str) -> int:
        """Net stock for a single item as of the request date."""
        return tools.check_stock(ctx, item_name)

    @jim.tool
    def order_quote(ctx: RunContext[Deps]) -> Dict:
        """Authoritative quote (catalog pricing + bulk-discount tier). Use these numbers."""
        return tools.order_quote(ctx)

    # ---- Stanley Hudson: Sales/Fulfillment ----
    stanley = Agent(
        model, deps_type=Deps, output_type=SaleResult,
        system_prompt=PERSONAS["stanley"]["prompt"],
    )

    @stanley.tool
    def record_sale(ctx: RunContext[Deps], item_name: str, quantity: int, total_price: float) -> int:
        """Record a sale for an item; returns the transaction id."""
        return tools.record_sale(ctx, item_name, quantity, total_price)

    @stanley.tool
    def cash_balance(ctx: RunContext[Deps]) -> float:
        """Current cash balance as of the request date."""
        return tools.cash_balance(ctx)

    @stanley.tool
    def delivery_estimate_stanley(ctx: RunContext[Deps], quantity: int) -> str:
        """Supplier delivery date for a quantity, based on the request date."""
        return tools.delivery_estimate(ctx, quantity)

    @stanley.tool
    def order_fulfillment(ctx: RunContext[Deps]) -> Dict:
        """Authoritative fulfill-or-decline decision for the parsed order."""
        return tools.order_fulfillment(ctx)

    # ---- David Wallace: Business Advisor ----
    david = Agent(
        model, deps_type=Deps, output_type=AdvisorNote,
        system_prompt=PERSONAS["david"]["prompt"],
    )

    @david.tool
    def financial_report_david(ctx: RunContext[Deps]) -> Dict:
        """Full financial report as of the request date."""
        return tools.financial_report(ctx)

    @david.tool
    def cash_balance_david(ctx: RunContext[Deps]) -> float:
        """Current cash balance as of the request date."""
        return tools.cash_balance(ctx)

    return {"michael": michael, "dwight": dwight, "jim": jim,
            "stanley": stanley, "david": david}
