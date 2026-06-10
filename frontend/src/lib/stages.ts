export const STAGE_ORDER = [
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

export type Stage = (typeof STAGE_ORDER)[number];

export const STAGE_FRIENDLY: Record<Stage, string> = {
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

export function friendlyStage(stage: string | null): string {
  if (!stage) return "Preparing…";
  if (stage === "done") return "Done";
  const known = STAGE_FRIENDLY[stage as Stage];
  return known ?? stage;
}

export type StageState = "pending" | "in_progress" | "done";

export function stageStates(
  currentStage: string | null,
): Array<{ stage: Stage; label: string; state: StageState }> {
  const idx = currentStage ? STAGE_ORDER.indexOf(currentStage as Stage) : -1;
  return STAGE_ORDER.map((stage, i) => ({
    stage,
    label: STAGE_FRIENDLY[stage],
    state: idx < 0
      ? "pending"
      : i < idx
        ? "done"
        : i === idx
          ? "in_progress"
          : "pending",
  }));
}
