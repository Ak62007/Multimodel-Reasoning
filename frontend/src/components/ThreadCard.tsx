import type { Thread } from "../types/api";
import { formatMMSS } from "../lib/time";
import { RelationBadge } from "./Badges";

export function ThreadCard({ thread: t }: { thread: Thread }) {
  return (
    <article
      className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5 space-y-3"
      data-testid="thread-card"
    >
      <header className="flex items-center gap-3 flex-wrap">
        <h3 className="text-sm font-medium text-neutral-100">{t.title}</h3>
        <RelationBadge relation={t.relation} />
      </header>
      <p className="text-sm leading-relaxed text-neutral-300">{t.summary}</p>
      <p className="text-sm leading-relaxed text-neutral-400">{t.interpretation}</p>
      {t.occurrences.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1" data-testid="thread-occurrences">
          <span className="text-xs text-neutral-500">Seen at:</span>
          {t.occurrences.map((o, i) => (
            <span
              key={i}
              className="rounded border border-sand/20 bg-sand/[0.08] px-1.5 py-0.5 font-mono text-[11px] text-sand/90"
            >
              {formatMMSS(o)}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
