"""Build pydantic-ai `Agent` instances bound to our prompts + output schemas.

Centralised so each per-agent runner just calls `make_agent(...)`. When
`LLM_PROVIDER=stub`, the runners short-circuit and never reach this module.

The concrete model provider is derived from the `LLM_MODEL` prefix:

  * ``google-gla:gemini-2.5-flash`` -> Gemini via the Google GLA provider
  * ``groq:llama-3.3-70b-versatile`` -> Groq
  * a bare id (no ``:``) is treated as a Groq model for backwards compat.

Swapping providers is therefore a `.env` change (plus the matching API key),
not a code change.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.providers.groq import GroqProvider

from agents._settings import AgentSettings

_GEMINI_PROVIDERS = {"google-gla", "google", "gemini"}


def _split_spec(llm_model: str) -> tuple[str, str]:
    """Split ``"<provider>:<model_id>"`` -> ``(provider, model_id)``.

    A bare model id (no ``:``) is treated as Groq for backwards compat.
    """
    if ":" in llm_model:
        provider, model_id = llm_model.split(":", 1)
        return provider.strip().lower(), model_id.strip()
    return "groq", llm_model.strip()


def _build_model(settings: AgentSettings) -> Model:
    provider, model_id = _split_spec(settings.llm_model)

    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError(
                f"LLM_MODEL={settings.llm_model!r} resolves to Groq but GROQ_API_KEY is not set. "
                "Set it in .env or env."
            )
        return GroqModel(model_name=model_id, provider=GroqProvider(api_key=settings.groq_api_key))

    if provider in _GEMINI_PROVIDERS:
        if not settings.gemini_api_key:
            raise RuntimeError(
                f"LLM_MODEL={settings.llm_model!r} resolves to Gemini but GEMINI_API_KEY is not set. "
                "Set it in .env or env."
            )
        return GeminiModel(
            model_name=model_id, provider=GoogleGLAProvider(api_key=settings.gemini_api_key)
        )

    raise RuntimeError(
        f"Unsupported LLM provider {provider!r} in LLM_MODEL={settings.llm_model!r}. "
        "Supported prefixes: 'groq:', 'google-gla:'."
    )


@lru_cache(maxsize=16)
def _cached_agent(settings_hash: tuple, system_prompt: str, output_type: type) -> Agent:
    """LRU-cached agent factory.

    Cached on (provider, model, key) + prompt + output_type so we don't
    re-build a pydantic-ai Agent and underlying client for every window.
    """
    settings = AgentSettings()  # re-read from env so we honour overrides
    model = _build_model(settings)
    return Agent(model=model, output_type=output_type, system_prompt=system_prompt)  # type: ignore[arg-type]


def make_agent[T: BaseModel](
    *, system_prompt: str, output_type: type[T], settings: AgentSettings | None = None
) -> Agent:
    settings = settings or AgentSettings()
    key = (
        settings.llm_provider,
        settings.llm_model,
        settings.groq_api_key or "",
        settings.gemini_api_key or "",
    )
    return _cached_agent(key, system_prompt, output_type)


__all__ = ["make_agent"]
