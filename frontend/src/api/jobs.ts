import type {
  IntegratedBehavioralReport,
  Job,
  LogsResponse,
  ReportResponse,
} from "../types/api";
import { apiFetch, apiUrl } from "./client";

export async function uploadJob(file: File, speakerLabel: string): Promise<Job> {
  const fd = new FormData();
  fd.append("video", file, file.name);
  fd.append("speaker_label", speakerLabel);
  return apiFetch<Job>("/api/jobs", {
    method: "POST",
    body: fd,
  });
}

export async function getJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${jobId}`);
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiFetch<void>(`/api/jobs/${jobId}`, { method: "DELETE" });
}

export async function getSegments(
  jobId: string,
): Promise<IntegratedBehavioralReport[]> {
  return apiFetch<IntegratedBehavioralReport[]>(`/api/jobs/${jobId}/segments`);
}

export async function getReport(jobId: string): Promise<ReportResponse> {
  return apiFetch<ReportResponse>(`/api/jobs/${jobId}/report`);
}

export async function getLogs(jobId: string, tail = 200): Promise<LogsResponse> {
  return apiFetch<LogsResponse>(`/api/jobs/${jobId}/logs?tail=${tail}`);
}

export function masterDfUrl(jobId: string, format: "parquet" | "json" = "parquet"): string {
  return apiUrl(`/api/jobs/${jobId}/master_df?format=${format}`);
}
