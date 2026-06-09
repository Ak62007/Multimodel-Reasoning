// API types — must match backend/app/schemas.py + agents/schemas.py.

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface Job {
  id: string;
  filename: string;
  status: JobStatus;
  current_stage: string | null;
  progress: number; // 0.0–1.0
  error: string | null;
  created_at: string;
  updated_at: string;
  duration_sec: number | null;
}

export interface JobList {
  items: Job[];
  total: number;
}

export type ToneLabel =
  | "Strong_Positive"
  | "Authentic"
  | "Mostly_Authentic"
  | "Mixed_Signals"
  | "Concerning";

export type PatternType = "Strength" | "Concern" | "Notable";
export type Significance = "Low" | "Medium" | "High";
export type Modality = "Visual" | "Audio" | "Verbal";

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
  overall_window_tone: ToneLabel;
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

export interface SegmentsResponse {
  items: IntegratedBehavioralReport[];
}

export interface LogsResponse {
  lines: string[];
}

export interface HealthResponse {
  status: "ok";
  version: string;
}

// Pipeline stage → user-facing label (spec §8.1, Screen 2 table).
export const STAGE_LABELS: Record<string, string> = {
  extracting_frames: "Extracting video frames…",
  extracting_audio: "Extracting audio track…",
  extracting_face_features: "Reading facial expressions…",
  extracting_audio_features: "Analyzing vocal characteristics…",
  transcribing: "Transcribing speech…",
  merging: "Aligning all signals on the timeline…",
  feature_engineering: "Computing behavioral features…",
  anomaly_detection: "Detecting behavioral anomalies…",
  building_master_df: "Building the master profile…",
  running_agents: "Running behavioral agents…",
  generating_final_report: "Writing the final report…",
};

// Ordered list of all 11 stages for the checklist UI.
export const ALL_STAGES = [
  "extracting_frames",
  "extracting_audio",
  "extracting_face_features",
  "extracting_audio_features",
  "transcribing",
  "merging",
  "feature_engineering",
  "anomaly_detection",
  "building_master_df",
  "running_agents",
  "generating_final_report",
] as const;
