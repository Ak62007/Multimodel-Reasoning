import type { IntegratedBehavioralReport } from "../types/api";
import { formatMMSS } from "../lib/time";
import { PatternRow } from "./PatternRow";
import { ToneBadge } from "./ToneBadge";

export function CrossModalSegment({ segment }: { segment: IntegratedBehavioralReport }) {
  return (
    <section
      className="rounded-lg border border-neutral-200 bg-white p-5 space-y-3 shadow-sm"
      data-testid="cross-modal-segment"
    >
      <header className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-mono text-neutral-700">
          {formatMMSS(segment.time_range_start)} – {formatMMSS(segment.time_range_end)}
        </h3>
        <ToneBadge tone={segment.overall_window_tone} />
      </header>
      <blockquote className="text-sm text-neutral-700 border-l-2 border-neutral-200 pl-3 italic">
        {segment.executive_summary}
      </blockquote>
      <div className="space-y-1 pt-2">
        {segment.key_insights.map((ins, i) => (
          <PatternRow key={i} insight={ins} />
        ))}
      </div>
    </section>
  );
}
