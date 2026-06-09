"""Build pydantic-ai `Agent` instances bound to our prompts + output schemas.

Centralised so each per-agent runner just calls `make_agent(...)`. When
`LLM_PROVIDER=stub`, the runners short-circuit and never reach this module.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from agents._settings import AgentSettings


def _build_groq_model(settings: AgentSettings) -> GroqModel:
    if not settings.groq_api_key:
        raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set. Set it in .env or env.")
    provider = GroqProvider(api_key=settings.groq_api_key)
    return GroqModel(model_name=settings.llm_model, provider=provider)


@lru_cache(maxsize=8)
def _cached_agent(settings_hash: tuple, system_prompt: str, output_type: type) -> Agent:
    """LRU-cached agent factory.

    Cached on (provider, model, prompt, output_type) so we don't re-build a
    pydantic-ai Agent and Groq client for every window.
    """
    _provider, _model, _key = settings_hash
    settings = AgentSettings()  # re-read from env so we honour overrides
    model = _build_groq_model(settings)
    return Agent(model=model, output_type=output_type, system_prompt=system_prompt)  # type: ignore[arg-type]


def make_agent[T: BaseModel](
    *, system_prompt: str, output_type: type[T], settings: AgentSettings | None = None
) -> Agent:
    settings = settings or AgentSettings()
    key = (settings.llm_provider, settings.llm_model, settings.groq_api_key or "")
    return _cached_agent(key, system_prompt, output_type)


__all__ = ["make_agent"]
