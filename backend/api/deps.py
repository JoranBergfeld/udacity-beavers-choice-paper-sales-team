from __future__ import annotations

from typing import Optional

from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from backend.api.config import CONFIG


def current_model() -> Optional[Model]:
    """Return the model the agents should use for this request.

    In demo mode (no API key) we use pydantic-ai's TestModel so the app is fully usable
    without credentials. Otherwise build the real OpenAI-compatible model from the UI
    config (model name + base URL), so the model picked in Setup actually drives calls.
    """
    if CONFIG.demo_mode:
        return TestModel()
    from backend.munder.agents import build_model

    return build_model(model_name=CONFIG.model, base_url=CONFIG.base_url)
