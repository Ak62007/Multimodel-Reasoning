import type { InterviewPhase, Modality, Relation, SignalKind } from "../types/api";

const kindStyles: Record<SignalKind, string> = {
  Strength: "bg-green-100 text-green-800 border-green-300",
  Tell: "bg-red-100 text-red-800 border-red-300",
  Tension: "bg-amber-100 text-amber-800 border-amber-300",
  Quirk: "bg-purple-100 text-purple-800 border-purple-300",
  Shift: "bg-blue-100 text-blue-800 border-blue-300",
};

export function KindBadge({ kind }: { kind: SignalKind }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${kindStyles[kind]}`}
      data-testid="kind-badge"
      data-kind={kind}
    >
      {kind}
    </span>
  );
}

const relationStyles: Record<Relation, string> = {
  Correlation: "bg-blue-50 text-blue-700 border-blue-200",
  Contradiction: "bg-red-50 text-red-700 border-red-200",
  Isolated: "bg-neutral-100 text-neutral-600 border-neutral-200",
};

const relationLabels: Record<Relation, string> = {
  Correlation: "Correlation",
  Contradiction: "Contradiction",
  Isolated: "Single-modality",
};

export function RelationBadge({ relation }: { relation: Relation }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${relationStyles[relation]}`}
      data-testid="relation-badge"
      data-relation={relation}
    >
      {relationLabels[relation]}
    </span>
  );
}

const phaseStyles: Record<InterviewPhase, string> = {
  Opening: "bg-sky-50 text-sky-700",
  Early: "bg-teal-50 text-teal-700",
  Middle: "bg-neutral-100 text-neutral-700",
  Late: "bg-orange-50 text-orange-700",
  Closing: "bg-rose-50 text-rose-700",
};

export function PhaseBadge({ phase }: { phase: InterviewPhase }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${phaseStyles[phase]}`}
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
          className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-600"
        >
          {m}
        </span>
      ))}
    </span>
  );
}
