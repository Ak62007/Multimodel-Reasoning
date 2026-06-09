"""MMR agentic layer.

Four agents (visual / audio / vocab observers + pattern detector) plus a final
judge. Only the pattern detector's `IntegratedBehavioralReport`s and the judge's
`FinalReport` are exposed publicly — observer outputs are internal scaffolding.

See spec section 9 for the design rationale.
"""

__all__: list[str] = []
