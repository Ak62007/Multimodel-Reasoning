import type { Highlight } from "../types/api";
import { formatMMSS } from "../lib/time";
import { KindBadge, ModalityChips } from "./Badges";
import { SignificancePill } from "./SignificancePill";

export function HighlightCard({ highlight: h }: { highlight: Highlight }) {
  return (
    <article
      className="group rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5 space-y-3 transition hover:border-sand/25 hover:bg-white/[0.03]"
      data-testid="highlight-card"
    >
      <header className="flex items-center gap-3 flex-wrap">
        <span
          className="rounded-md border border-sand/25 bg-sand/10 px-2.5 py-1 font-mono text-sm font-semibold text-sand"
          data-testid="highlight-timestamp"
          title="Scrub to this moment in the video"
        >
          {formatMMSS(h.ts_start)} – {formatMMSS(h.ts_end)}
        </span>
        <KindBadge kind={h.kind} />
        <SignificancePill value={h.significance} />
        <ModalityChips modalities={h.modalities} />
      </header>
      <h3 className="text-base font-medium text-neutral-100">{h.title}</h3>
      <p className="text-sm leading-relaxed text-neutral-300">{h.what_happened}</p>
      <p className="text-sm leading-relaxed text-neutral-400">
        <span className="font-medium text-neutral-500">Why it matters: </span>
        {h.why_it_matters}
      </p>
    </article>
  );
}
