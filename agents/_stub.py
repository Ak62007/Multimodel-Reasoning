"""Deterministic stub provider for tests and CI.

When ``LLM_PROVIDER=stub`` the agent orchestrator routes every call through
this module instead of Groq. The full implementation lands in M4 — M1
ships an importable placeholder so the layout in §6 is in place.
"""

from __future__ import annotations
