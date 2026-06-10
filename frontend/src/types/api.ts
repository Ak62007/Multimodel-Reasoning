// Mirrors backend/app/schemas.py + agents/schemas.py. Keep in sync.

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface Job {
  id: string;
  filename: string;
  status: JobStatus;
  current_stage: string | null;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  duration_sec: number | null;
}

export interface JobList {
  items: Job[];
  total: number;
}

export type PatternType = "Strength" | "Concern" | "Notable";
export type Significance = "Low" | "Medium" | "High";
export type Modality = "Visual" | "Audio" | "Verbal";
export type WindowTone =
  | "Strong_Positive"
  | "Authentic"
  | "Mostly_Authentic"
  | "Mixed_Signals"
  | "Concerning";

export interface CrossModalInsight {
  timestamp_start: number;
  timestamp_end: number;
  spoken_content: string;
  modalities_involved: Modality[];
  pattern_type: PatternType;
  significance: Significance;
  observation: string;
  interpretation: string;
}

export interface IntegratedBehavioralReport {
  time_range_start: number;
  time_range_end: number;
  overall_window_tone: WindowTone;
  executive_summary: string;
  key_insights: CrossModalInsight[];
}

export interface FinalReport {
  executive_summary: string;
  behavioral_strengths: string;
  vulnerabilities_and_triggers: string;
  areas_for_improvement: string;
}

export interface ReportResponse {
  markdown: string;
  structured: FinalReport;
}

export interface LogsResponse {
  lines: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
}
