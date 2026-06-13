import { api } from "./client";
import type {
  HealthResponse,
  Job,
  JobList,
  LogsResponse,
  ReportResponse,
  SegmentsResponse,
} from "../types/api";

export const jobsApi = {
  health: () => api.get<HealthResponse>("/api/health"),

  createJob: (file: File) => {
    // The interviewee speaker is auto-detected server-side; no label is sent.
    const form = new FormData();
    form.append("video", file);
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
