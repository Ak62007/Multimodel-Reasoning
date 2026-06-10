import type { PatternType } from "../types/api";

const STYLES: Record<PatternType, { bg: string; text: string; color: string }> = {
  Strength: { bg: "bg-emerald-100", text: "text-emerald-800", color: "green" },
  Concern: { bg: "bg-red-100", text: "text-red-800", color: "red" },
  Notable: { bg: "bg-amber-100", text: "text-amber-800", color: "amber" },
};

interface PatternTypeBadgeProps {
  patternType: PatternType;
}

export default function PatternTypeBadge({ patternType }: PatternTypeBadgeProps) {
  const style = STYLES[patternType];
  return (
    <span
      className={`inline-flex items-center rounded ${style.bg} ${style.text} px-2 py-0.5 text-xs font-medium`}
      data-testid="pattern-type-badge"
      data-color={style.color}
    >
      {patternType}
    </span>
  );
}
