import type { Significance } from "../types/api";

interface SignificancePillProps {
  significance: Significance;
}

export default function SignificancePill({ significance }: SignificancePillProps) {
  return (
    <span
      className="inline-flex items-center rounded-full border border-neutral-300 px-2 py-0.5 text-xs text-neutral-600"
      data-testid="significance-pill"
    >
      {significance}
    </span>
  );
}
