import type { InterviewPhase, Modality, Relation, SignalKind } from "../types/api";

// Minimal: badges are neutral chips. Kind keeps a small, muted dot so the
// category still reads at a glance without flooding the page with colour.
const kindDot: Record<SignalKind, string> = {
  Strength: "bg-emerald-400/80",
  Tell: "bg-rose-400/80",
  Tension: "bg-amber-400/80",
  Quirk: "bg-violet-400/80",
  Shift: "bg-sky-400/80",
};

export function KindBadge({ kind }: { kind: SignalKind }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-[11px] font-medium text-neutral-300"
      data-testid="kind-badge"
      data-kind={kind}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${kindDot[kind]}`} />
      {kind}
    </span>
  );
}

const relationLabels: Record<Relation, string> = {
  Correlation: "Correlation",
  Contradiction: "Contradiction",
  Isolated: "Single-modality",
};

export function RelationBadge({ relation }: { relation: Relation }) {
  return (
    <span
      className="inline-flex items-center rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-medium text-neutral-400"
      data-testid="relation-badge"
      data-relation={relation}
    >
      {relationLabels[relation]}
    </span>
  );
}

export function PhaseBadge({ phase }: { phase: InterviewPhase }) {
  return (
    <span
      className="inline-flex items-center rounded bg-white/[0.05] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-neutral-400"
      data-testid="phase-badge"
      data-phase={phase}
    >
      {phase}
    </span>
  );
}

export function ModalityChips({ modalities }: { modalities: Modality[] }) {
  if (!modalities.length) return null;
  return (
    <span className="flex flex-wrap gap-1" data-testid="modality-chips">
      {modalities.map((m) => (
        <span
          key={m}
          className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-[10px] text-neutral-400"
        >
          {m}
        </span>
      ))}
    </span>
  );
}
