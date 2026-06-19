"""MMR agentic layer.

Six agents: visual / audio / vocab observers feed a per-window Window Analyst
(producing a `WindowAnalysis` field note for every window), and a Pattern Weaver
+ Narrative Editor synthesise the chronological journal into the final
`FinalReport`. Observer outputs are internal scaffolding; the journal
(`WindowAnalysis` list) and `FinalReport` are exposed publicly.
"""

__all__: list[str] = []
