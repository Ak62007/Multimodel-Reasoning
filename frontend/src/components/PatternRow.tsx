import type { CrossModalInsight } from "../types/api";
import { formatMMSS } from "../lib/time";
import PatternTypeBadge from "./PatternTypeBadge";
import SignificancePill from "./SignificancePill";

interface PatternRowProps {
  insight: CrossModalInsight;
}

export default function PatternRow({ insight }: PatternRowProps) {
  return (
    <div className="border-t border-neutral-200 py-4" data-testid="pattern-row">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-neutral-700">
          {formatMMSS(insight.timestamp_start)}
        </span>
        <PatternTypeBadge patternType={insight.pattern_type} />
        <SignificancePill significance={insight.significance} />
        {insight.modalities_involved.map((m) => (
          <span
            key={m}
            className="rounded-full border border-neutral-300 px-2 py-0.5 text-xs text-neutral-600"
          >
            {m}
          </span>
        ))}
      </div>

      {insight.spoken_content && (
        <blockquote className="mt-2 border-l-2 border-neutral-300 pl-3 text-sm italic text-neutral-600">
          “{insight.spoken_content}”
        </blockquote>
      )}
      <p className="mt-2 text-sm text-neutral-800">{insight.observation}</p>
      <p className="mt-1 pl-3 text-sm text-neutral-600">{insight.interpretation}</p>
    </div>
  );
}
