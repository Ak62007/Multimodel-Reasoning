// localStorage helpers. Keys are namespaced under "mmr:" so they don't
// collide with anything else served from the same origin.

const ACTIVE_KEY = "mmr:active-job-id";
const RECENT_KEY = "mmr:recent-jobs";
const RECENT_LIMIT = 5;

export interface RecentJob {
  id: string;
  filename: string;
  finishedAt: string; // ISO
}

export function getActiveJobId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_KEY);
  } catch {
    return null;
  }
}

export function setActiveJobId(id: string | null): void {
  try {
    if (id === null) localStorage.removeItem(ACTIVE_KEY);
    else localStorage.setItem(ACTIVE_KEY, id);
  } catch {
    // ignore quota / privacy-mode errors
  }
}

export function getRecentJobs(): RecentJob[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentJob[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushRecentJob(job: RecentJob): void {
  try {
    const current = getRecentJobs().filter((j) => j.id !== job.id);
    const next = [job, ...current].slice(0, RECENT_LIMIT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function removeRecentJob(id: string): void {
  try {
    const next = getRecentJobs().filter((j) => j.id !== id);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}
