from __future__ import annotations

import os
from dataclasses import dataclass, field


def _provider() -> str:
    return os.environ.get("MUNDER_PROVIDER", "openai").lower()


def _default_model() -> str:
    if _provider() == "azure":
        return os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get(
            "MUNDER_MODEL", "gpt-4o"
        )
    return os.environ.get("MUNDER_MODEL", "gpt-4o")


def _default_endpoint() -> str:
    if _provider() == "azure":
        return os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    return os.environ.get("UDACITY_BASE_URL", "https://openai.vocareum.com/v1")


@dataclass
class Config:
    """In-process app config. The real API key is never stored here or returned to the
    client, only whether one is present in the environment for the active provider."""

    provider: str = field(default_factory=_provider)
    model: str = field(default_factory=_default_model)
    base_url: str = field(default_factory=_default_endpoint)

    @property
    def api_key_set(self) -> bool:
        if self.provider == "azure":
            return bool(os.environ.get("AZURE_OPENAI_API_KEY"))
        return bool(os.environ.get("UDACITY_OPENAI_API_KEY"))

    @property
    def demo_mode(self) -> bool:
        """No API key for the active provider -> run with TestModel so the app is usable."""
        return not self.api_key_set

    def public_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_set": self.api_key_set,
            "demo_mode": self.demo_mode,
        }


CONFIG = Config()
