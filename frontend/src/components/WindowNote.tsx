import type { Signal, WindowAnalysis } from "../types/api";
import { formatMMSS } from "../lib/time";
import { KindBadge, ModalityChips, PhaseBadge, RelationBadge } from "./Badges";
import { SignificancePill } from "./SignificancePill";

export function WindowNote({ note }: { note: WindowAnalysis }) {
  const interesting = note.window_interest !== "Low";
  return (
    <details
      className="rounded-lg border border-neutral-200 bg-white shadow-sm"
      data-testid="window-note"
      open={interesting}
    >
      <summary className="cursor-pointer list-none px-4 py-3 flex items-center gap-3 flex-wrap">
        <span className="font-mono text-sm text-neutral-700">
          {formatMMSS(note.time_start)} – {formatMMSS(note.time_end)}
        </span>
        <PhaseBadge phase={note.phase} />
        <SignificancePill value={note.window_interest} />
        {note.signals.length > 0 && (
          <span className="text-xs text-neutral-500">
            {note.signals.length} signal{note.signals.length === 1 ? "" : "s"}
          </span>
        )}
      </summary>

      <div className="px-4 pb-4 space-y-3">
        {note.spoken_excerpt && note.spoken_excerpt !== "[no transcript]" && (
          <blockquote className="border-l-2 border-neutral-200 pl-3 text-sm italic text-neutral-700">
            “{note.spoken_excerpt}”
          </blockquote>
        )}
        <p className="text-sm text-neutral-800">{note.narrative}</p>
        <dl className="grid grid-cols-1 gap-1 text-xs text-neutral-600 sm:grid-cols-3">
          <Read label="Face" value={note.visual_read} />
          <Read label="Voice" value={note.audio_read} />
          <Read label="Speech" value={note.verbal_read} />
        </dl>
        {note.signals.length > 0 && (
          <div className="space-y-2 pt-1">
            {note.signals.map((s, i) => (
              <SignalRow key={i} signal={s} />
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

function Read({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <dt className="font-medium text-neutral-400">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function SignalRow({ signal: s }: { signal: Signal }) {
  return (
    <div className="border-l-2 border-neutral-200 pl-3 py-1 space-y-1" data-testid="signal-row">
      <div className="flex items-center gap-2 flex-wrap text-xs text-neutral-500">
        <span className="font-mono">{formatMMSS(s.timestamp_start)}</span>
        <KindBadge kind={s.kind} />
        <RelationBadge relation={s.relation} />
        <ModalityChips modalities={s.modalities} />
      </div>
      <div className="text-sm font-medium text-neutral-900">{s.headline}</div>
      {s.spoken_content && (
        <blockquote className="border-l-2 border-neutral-100 pl-2 text-xs italic text-neutral-600">
          “{s.spoken_content}”
        </blockquote>
      )}
      <div className="text-sm text-neutral-700">{s.evidence}</div>
      <div className="text-sm text-neutral-500">{s.interpretation}</div>
    </div>
  );
}
