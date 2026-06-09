import type { CrossModalInsight } from "../types/api";
import { formatMMSS } from "../lib/time";
import { PatternTypeBadge } from "./PatternTypeBadge";
import { SignificancePill } from "./SignificancePill";

export function PatternRow({ insight }: { insight: CrossModalInsight }) {
  return (
    <div className="border-l-2 border-neutral-200 pl-4 py-3 space-y-2" data-testid="pattern-row">
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="font-mono">{formatMMSS(insight.timestamp_start)}</span>
        <PatternTypeBadge type={insight.pattern_type} />
        <SignificancePill value={insight.significance} />
        <span className="flex gap-1">
          {insight.modalities_involved.map((m) => (
            <span
              key={m}
              className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-600"
            >
              {m}
            </span>
          ))}
        </span>
      </div>
      <blockquote className="italic text-sm text-neutral-700 border-l-2 border-neutral-100 pl-3">
        “{insight.spoken_content}”
      </blockquote>
      <div className="text-sm text-neutral-900">{insight.observation}</div>
      <div className="text-sm text-neutral-600 pl-3">{insight.interpretation}</div>
    </div>
  );
}
