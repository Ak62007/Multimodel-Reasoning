import type { IntegratedBehavioralReport } from "../types/api";
import { formatMMSS } from "../lib/time";
import ToneBadge from "./ToneBadge";
import PatternRow from "./PatternRow";

interface CrossModalSegmentProps {
  report: IntegratedBehavioralReport;
}

export default function CrossModalSegment({ report }: CrossModalSegmentProps) {
  return (
    <article
      className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm"
      data-testid="cross-modal-segment"
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-medium text-neutral-900">
          {formatMMSS(report.time_range_start)} – {formatMMSS(report.time_range_end)}
        </h3>
        <ToneBadge tone={report.overall_window_tone} />
      </header>
      <blockquote className="mt-2 border-l-2 border-neutral-300 pl-3 text-sm text-neutral-600">
        {report.executive_summary}
      </blockquote>
      <div className="mt-2">
        {report.key_insights.map((insight, i) => (
          <PatternRow key={i} insight={insight} />
        ))}
      </div>
    </article>
  );
}
