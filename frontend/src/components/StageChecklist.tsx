import { ALL_STAGES, STAGE_LABELS } from "../types/api";

interface Props {
  currentStage: string | null;
}

export function StageChecklist({ currentStage }: Props) {
  const idx = currentStage ? ALL_STAGES.indexOf(currentStage as typeof ALL_STAGES[number]) : -1;
  return (
    <ol className="space-y-1.5 text-sm" data-testid="stage-checklist">
      {ALL_STAGES.map((stage, i) => {
        const state: "pending" | "active" | "done" =
          i < idx ? "done" : i === idx ? "active" : "pending";
        return (
          <li
            key={stage}
            data-testid={`stage-${stage}`}
            data-state={state}
            className={`flex items-center gap-2.5 ${
              state === "active" ? "text-neutral-100 font-medium" : ""
            } ${state === "done" ? "text-neutral-400" : ""} ${
              state === "pending" ? "text-neutral-600" : ""
            }`}
          >
            <span
              aria-hidden="true"
              className={`inline-block w-4 text-center ${
                state === "done" || state === "active" ? "text-sand" : ""
              } ${state === "active" ? "animate-pulse-dot" : ""}`}
            >
              {state === "done" ? "✓" : state === "active" ? "◐" : "◯"}
            </span>
            <span>{STAGE_LABELS[stage] ?? stage}</span>
          </li>
        );
      })}
    </ol>
  );
}
