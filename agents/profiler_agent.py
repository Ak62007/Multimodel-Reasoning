"""Pattern Detector (formerly "Profiler") — public output.

Consumes the three observer outputs + transcript slice for one window, returns
an `IntegratedBehavioralReport`. Selectively reports only meaningful cross-modal
patterns (Strength / Concern / Notable); empty `key_insights` means the window
is silently dropped from the public report. Implemented in M4.
"""

from __future__ import annotations

__all__: list[str] = []
