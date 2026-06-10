const ACTIVE_KEY = "mmr.activeJobId";
const RECENT_KEY = "mmr.recentJobs";
const MAX_RECENT = 5;

export interface RecentEntry {
  id: string;
  filename: string;
  completedAt: string;
}

const isBrowser = typeof window !== "undefined";

export function getActiveJobId(): string | null {
  if (!isBrowser) return null;
  return window.localStorage.getItem(ACTIVE_KEY);
}

export function setActiveJobId(jobId: string | null): void {
  if (!isBrowser) return;
  if (jobId) {
    window.localStorage.setItem(ACTIVE_KEY, jobId);
  } else {
    window.localStorage.removeItem(ACTIVE_KEY);
  }
}

export function getRecentJobs(): RecentEntry[] {
  if (!isBrowser) return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item) =>
        typeof item?.id === "string" &&
        typeof item?.filename === "string" &&
        typeof item?.completedAt === "string",
    );
  } catch {
    return [];
  }
}

export function recordRecentJob(entry: RecentEntry): void {
  if (!isBrowser) return;
  const existing = getRecentJobs().filter((e) => e.id !== entry.id);
  const next = [entry, ...existing].slice(0, MAX_RECENT);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function clearRecentJob(jobId: string): void {
  if (!isBrowser) return;
  const next = getRecentJobs().filter((e) => e.id !== jobId);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}
