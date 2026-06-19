import { api } from "./client";
import type {
  HealthResponse,
  Job,
  JobList,
  LogsResponse,
  ReportResponse,
  SegmentsResponse,
  Tier,
} from "../types/api";

export const jobsApi = {
  health: () => api.get<HealthResponse>("/api/health"),

  createJob: (
    file: File,
    opts?: { geminiApiKey?: string; assemblyaiApiKey?: string; tier?: Tier },
  ) => {
    // The interviewee speaker is auto-detected server-side; no label is sent.
    // API keys (BYOK) are sent per-request and never stored server-side.
    const form = new FormData();
    form.append("video", file);
    if (opts?.tier) form.append("tier", opts.tier);
    if (opts?.geminiApiKey) form.append("gemini_api_key", opts.geminiApiKey);
    if (opts?.assemblyaiApiKey) form.append("assemblyai_api_key", opts.assemblyaiApiKey);
    return api.post<Job>("/api/jobs", form);
  },

  getJob: (id: string) => api.get<Job>(`/api/jobs/${id}`),

  listJobs: (opts: { status?: string; limit?: number; offset?: number } = {}) => {
    const params = new URLSearchParams();
    if (opts.status) params.set("status", opts.status);
    if (opts.limit != null) params.set("limit", String(opts.limit));
    if (opts.offset != null) params.set("offset", String(opts.offset));
    const qs = params.toString();
    return api.get<JobList>(`/api/jobs${qs ? `?${qs}` : ""}`);
  },

  deleteJob: (id: string) => api.delete<void>(`/api/jobs/${id}`),

  getSegments: (id: string) =>
    api.get<SegmentsResponse>(`/api/jobs/${id}/segments`),

  getReport: (id: string) => api.get<ReportResponse>(`/api/jobs/${id}/report`),

  getLogs: (id: string, tail: number = 200) =>
    api.get<LogsResponse>(`/api/jobs/${id}/logs?tail=${tail}`),
};
