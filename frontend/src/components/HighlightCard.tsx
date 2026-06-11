import type { Highlight } from "../types/api";
import { formatMMSS } from "../lib/time";
import { KindBadge, ModalityChips } from "./Badges";
import { SignificancePill } from "./SignificancePill";

export function HighlightCard({ highlight: h }: { highlight: Highlight }) {
  return (
    <article
      className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm space-y-3"
      data-testid="highlight-card"
    >
      <header className="flex items-center gap-3 flex-wrap">
        <span
          className="rounded-md bg-neutral-900 px-2.5 py-1 font-mono text-sm font-semibold text-white"
          data-testid="highlight-timestamp"
          title="Scrub to this moment in the video"
        >
          {formatMMSS(h.ts_start)} – {formatMMSS(h.ts_end)}
        </span>
        <KindBadge kind={h.kind} />
        <SignificancePill value={h.significance} />
        <ModalityChips modalities={h.modalities} />
      </header>
      <h3 className="text-base font-semibold text-neutral-900">{h.title}</h3>
      <p className="text-sm text-neutral-800">{h.what_happened}</p>
      <p className="text-sm text-neutral-600">
        <span className="font-medium text-neutral-500">Why it matters: </span>
        {h.why_it_matters}
      </p>
    </article>
  );
}
