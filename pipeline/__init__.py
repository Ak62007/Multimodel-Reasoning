"""Multimodal interview analysis pipeline.

This package owns the deterministic, non-LLM data path that turns a raw
interview video into a per-time-step master dataframe of behavioural
features plus anomaly flags. The agentic / LLM layer lives in
:mod:`agents` and consumes the output of :mod:`pipeline.orchestrator`.
"""

__all__: list[str] = []
