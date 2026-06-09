import type { ToneLabel } from "../types/api";

const styles: Record<ToneLabel, string> = {
  Strong_Positive: "bg-green-100 text-green-800 border-green-300",
  Authentic: "bg-green-50 text-green-700 border-green-200",
  Mostly_Authentic: "bg-neutral-100 text-neutral-700 border-neutral-300",
  Mixed_Signals: "bg-amber-100 text-amber-800 border-amber-300",
  Concerning: "bg-red-100 text-red-800 border-red-300",
};

const labels: Record<ToneLabel, string> = {
  Strong_Positive: "Strong Positive",
  Authentic: "Authentic",
  Mostly_Authentic: "Mostly Authentic",
  Mixed_Signals: "Mixed Signals",
  Concerning: "Concerning",
};

export function ToneBadge({ tone }: { tone: ToneLabel }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[tone]}`}
      data-testid="tone-badge"
      data-tone={tone}
    >
      {labels[tone]}
    </span>
  );
}
