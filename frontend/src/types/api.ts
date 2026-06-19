// API types — must match backend/app/schemas.py + agents/schemas.py.

export type JobStatus = "queued" | "running" | "succeeded" | "failed";
export type Tier = "free" | "paid";

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
  tier: Tier | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

export interface JobList {
  items: Job[];
  total: number;
}

export type Significance = "Low" | "Medium" | "High";
export type Modality = "Visual" | "Audio" | "Verbal";
export type Relation = "Correlation" | "Contradiction" | "Isolated";
export type SignalKind = "Strength" | "Tell" | "Tension" | "Quirk" | "Shift";
export type InterviewPhase = "Opening" | "Early" | "Middle" | "Late" | "Closing";

// One discrete finding inside a window (single- or cross-modal).
export interface Signal {
  timestamp_start: number;
  timestamp_end: number;
  modalities: Modality[];
  relation: Relation;
  kind: SignalKind;
  headline: string;
  evidence: string;
  spoken_content: string;
  interpretation: string;
  significance: Significance;
}

// One window's field note — the chronological "journal" entry.
export interface WindowAnalysis {
  time_start: number;
  time_end: number;
  phase: InterviewPhase;
  position_pct: number;
  spoken_excerpt: string;
  visual_read: string;
  audio_read: string;
  verbal_read: string;
  narrative: string;
  window_interest: Significance;
  signals: Signal[];
}

// A "go watch this moment" entry — the report's centrepiece.
export interface Highlight {
  ts_start: number;
  ts_end: number;
  title: string;
  what_happened: string;
  why_it_matters: string;
  modalities: Modality[];
  kind: SignalKind;
  significance: Significance;
}

// A recurring pattern across multiple windows.
export interface Thread {
  title: string;
  summary: string;
  relation: Relation;
  occurrences: number[];
  interpretation: string;
}

export interface FinalReport {
  headline: string;
  overview: string;
  behavioral_arc: string;
  highlights: Highlight[];
  threads: Thread[];
  coaching_notes: string;
}

export interface ReportResponse {
  markdown: string;
  structured: FinalReport;
}

export interface SegmentsResponse {
  items: WindowAnalysis[];
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

// A warm one-liner shown under the active stage, so the wait feels human.
export const STAGE_BLURBS: Record<string, string> = {
  extracting_frames: "Taking the video apart, frame by frame.",
  extracting_audio: "Lifting the audio off the video.",
  extracting_face_features: "Watching every blink, glance and micro-expression.",
  extracting_audio_features: "Listening for shifts in pitch, pace and energy.",
  transcribing: "Turning speech into words — and who said what.",
  merging: "Lining face, voice and words up on one timeline.",
  feature_engineering: "Turning raw signals into behavioral cues.",
  anomaly_detection: "Spotting the moments that stand out.",
  building_master_df: "Assembling the full picture.",
  running_agents:
    "The deep read — the agents study every moment together. This is the longest step, so grab a coffee. ☕",
  generating_final_report: "Weaving everything into your report.",
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
