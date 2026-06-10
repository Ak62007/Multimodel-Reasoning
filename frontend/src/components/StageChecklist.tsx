import { stageStates } from "../lib/stages";

interface StageChecklistProps {
  currentStage: string | null;
}

const ICONS = {
  pending: "◯",
  in_progress: "◐",
  done: "✓",
} as const;

export default function StageChecklist({ currentStage }: StageChecklistProps) {
  const stages = stageStates(currentStage);
  return (
    <ol className="mt-6 space-y-2 text-sm" data-testid="stage-checklist">
      {stages.map(({ stage, label, state }) => (
        <li
          key={stage}
          className={[
            "flex items-center gap-3",
            state === "done" && "text-neutral-500",
            state === "in_progress" && "font-medium text-neutral-900 animate-pulse",
            state === "pending" && "text-neutral-400",
          ]
            .filter(Boolean)
            .join(" ")}
          data-state={state}
          data-stage={stage}
        >
          <span aria-hidden className="inline-block w-4 text-center">
            {ICONS[state]}
          </span>
          <span>{label}</span>
        </li>
      ))}
    </ol>
  );
}
