"""Stub provider for deterministic agent outputs.

When `LLM_PROVIDER=stub`, every agent runner returns a canned Pydantic
instance derived directly from its structured input — no LLM call is made.
Used by the test suite (no token cost, no flakiness) and by the backend in
`MMR_TEST_MODE=1`.

The stub outputs are intentionally simple but schema-correct so downstream
consumers (Window Analyst → Pattern Weaver → Narrative Editor → frontend)
get sensible, non-empty data. Crucially, unlike the real agents the stub is
deterministic — given the same inputs it always returns the same output.
"""

from __future__ import annotations

from agents.schemas import (
    AudioObservation,
    FinalReport,
    Highlight,
    Signal,
    Thread,
    VisualObservation,
    VocabObservation,
    WeaverDraft,
    WindowAnalysis,
)


def _summary_from_anomalies(label: str, n: int) -> str:
    if n == 0:
        return f"{label} baseline — no anomalies observed."
    return f"{label} showed {n} anomalous event{'s' if n != 1 else ''} during this window."


# --- Observers -------------------------------------------------------------


def stub_visual(start: float, end: float, events: list, raw_summary: str = "") -> VisualObservation:
    return VisualObservation(
        time_range_start=start,
        time_range_end=end,
        overall_visual_state="Baseline" if not events else "Low_Stress",
        detected_anomalies=events,
        raw_summary=raw_summary or _summary_from_anomalies("Visual", len(events)),
        contradiction_context=_summary_from_anomalies("Visual", len(events)),
    )


def stub_audio(start: float, end: float, events: list, raw_summary: str = "") -> AudioObservation:
    return AudioObservation(
        time_range_start=start,
        time_range_end=end,
        overall_vocal_state="Baseline_Calm" if not events else "Stressed/Tight",
        detected_anomalies=events,
        raw_summary=raw_summary or _summary_from_anomalies("Vocal", len(events)),
        contradiction_context=_summary_from_anomalies("Vocal", len(events)),
    )


def stub_vocab(start: float, end: float, events: list, raw_summary: str = "") -> VocabObservation:
    return VocabObservation(
        time_range_start=start,
        time_range_end=end,
        overall_verbal_state="Baseline_Fluent" if not events else "Cognitively_Overloaded",
        detected_anomalies=events,
        raw_summary=raw_summary or _summary_from_anomalies("Verbal", len(events)),
        contradiction_context=_summary_from_anomalies("Verbal", len(events)),
    )


# --- Window Analyst --------------------------------------------------------


def stub_window_analysis(
    start: float,
    end: float,
    phase: str,
    position_pct: float,
    visual: VisualObservation,
    audio: AudioObservation,
    vocab: VocabObservation,
    transcript: str,
) -> WindowAnalysis:
    """Always returns a populated WindowAnalysis — no empty-drop gate.

    One `Isolated` signal per active modality, plus a cross-modal
    `Correlation` signal when 2+ modalities are active.
    """
    excerpt = transcript[:160].strip()
    active: list[str] = []
    if visual.detected_anomalies:
        active.append("Visual")
    if audio.detected_anomalies:
        active.append("Audio")
    if vocab.detected_anomalies:
        active.append("Verbal")

    signals: list[Signal] = []
    for mod in active:
        signals.append(
            Signal(
                timestamp_start=start,
                timestamp_end=end,
                modalities=[mod],  # type: ignore[list-item]
                relation="Isolated",
                kind="Tell",
                headline=f"{mod} anomaly",
                evidence=f"{mod} signal deviated from baseline in this window.",
                spoken_content=excerpt,
                interpretation=f"A single-modality {mod.lower()} shift worth noting.",
                significance="Medium",
            )
        )
    if len(active) >= 2:
        signals.append(
            Signal(
                timestamp_start=start,
                timestamp_end=end,
                modalities=active,  # type: ignore[arg-type]
                relation="Correlation",
                kind="Tension",
                headline=f"{' + '.join(active)} move together",
                evidence=f"Anomalies aligned across {', '.join(active)}.",
                spoken_content=excerpt,
                interpretation="Multiple channels deviated at once — a stronger moment.",
                significance="High",
            )
        )

    if not active:
        narrative = "Steady baseline window — face, voice and speech all sit at rest."
        interest = "Low"
    elif len(active) == 1:
        narrative = f"A lone {active[0].lower()} shift stands out against an otherwise calm window."
        interest = "Medium"
    else:
        narrative = (
            f"Several channels move together here ({', '.join(active)}) — the most "
            "telling kind of moment."
        )
        interest = "High"

    return WindowAnalysis(
        time_start=start,
        time_end=end,
        phase=phase,  # type: ignore[arg-type]
        position_pct=position_pct,
        spoken_excerpt=excerpt or "[no transcript]",
        visual_read=visual.raw_summary or visual.contradiction_context,
        audio_read=audio.raw_summary or audio.contradiction_context,
        verbal_read=vocab.raw_summary or vocab.contradiction_context,
        narrative=narrative,
        window_interest=interest,  # type: ignore[arg-type]
        signals=signals,
    )


# --- Synthesis -------------------------------------------------------------


def stub_pattern_weaver(analyses: list[WindowAnalysis]) -> WeaverDraft:
    all_signals = [(a, s) for a in analyses for s in a.signals]
    high = [pair for pair in all_signals if pair[1].significance == "High"]
    chosen = high or all_signals

    highlights = [
        Highlight(
            ts_start=s.timestamp_start,
            ts_end=s.timestamp_end,
            title=s.headline,
            what_happened=s.evidence,
            why_it_matters=s.interpretation,
            modalities=s.modalities,
            kind=s.kind,
            significance=s.significance,
        )
        for _a, s in chosen[:10]
    ]

    # Build threads by grouping signals of the same kind that recur.
    by_kind: dict[str, list[float]] = {}
    relation_by_kind: dict[str, str] = {}
    for _a, s in all_signals:
        by_kind.setdefault(s.kind, []).append(s.timestamp_start)
        relation_by_kind[s.kind] = s.relation
    threads = [
        Thread(
            title=f"Recurring {kind} moments",
            summary=f"{len(times)} '{kind}' signal(s) across the interview.",
            relation=relation_by_kind[kind],  # type: ignore[arg-type]
            occurrences=sorted(times),
            interpretation=f"The candidate repeatedly produced {kind}-type signals.",
        )
        for kind, times in by_kind.items()
        if len(times) >= 2
    ]

    return WeaverDraft(
        headline=(
            f"Stub synthesis over {len(analyses)} window(s): "
            f"{len(highlights)} highlight(s), {len(threads)} recurring thread(s)."
        ),
        arc_notes=(
            "Stub arc: baseline established early; the active windows above mark the "
            "deviations. Run with a real LLM provider for genuine arc analysis."
        ),
        highlights=highlights,
        threads=threads,
    )


def stub_narrative_editor(draft: WeaverDraft) -> FinalReport:
    return FinalReport(
        headline=draft.headline,
        overview=(
            "**Stub mode.** This overview would normally be written by the Narrative "
            f"Editor from {len(draft.highlights)} highlight(s). Run with "
            "`LLM_PROVIDER=google-gla` for the real narrative."
        ),
        behavioral_arc=draft.arc_notes,
        highlights=draft.highlights,
        threads=draft.threads,
        coaching_notes=(
            "**Stub mode.** Real coaching notes would be tailored to the observed threads."
        ),
    )


__all__ = [
    "stub_audio",
    "stub_narrative_editor",
    "stub_pattern_weaver",
    "stub_visual",
    "stub_vocab",
    "stub_window_analysis",
]
