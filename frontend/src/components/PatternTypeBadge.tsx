import type { PatternType } from "../types/api";

const styles: Record<PatternType, string> = {
  Strength: "bg-green-100 text-green-800",
  Concern: "bg-red-100 text-red-800",
  Notable: "bg-amber-100 text-amber-800",
};

export function PatternTypeBadge({ type }: { type: PatternType }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${styles[type]}`}
      data-testid="pattern-type-badge"
      data-type={type}
    >
      {type}
    </span>
  );
}
