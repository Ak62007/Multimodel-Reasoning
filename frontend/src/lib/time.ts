/**
 * Parse a server timestamp into a Date. If the backend ever emits a tz-naive
 * ISO string (no `Z` / offset), JS would parse it as *local* time — on a
 * UTC+5:30 client that pushes a just-started job's elapsed timer to ~330m.
 * Treat an offset-less timestamp as UTC.
 */
export function parseServerDate(value: string): Date {
  const hasTz = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasTz ? value : `${value}Z`);
}

export function formatMMSS(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatElapsed(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
