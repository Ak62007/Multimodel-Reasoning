import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { deleteJob, getJob } from "../api/jobs";
import { friendlyStage } from "../lib/stages";
import { formatElapsed } from "../lib/time";
import { recordRecentJob } from "../lib/storage";
import StageChecklist from "../components/StageChecklist";

interface AnalyzingScreenProps {
  jobId: string;
  onSucceeded: () => void;
  onFailed: () => void;
  onCancel: () => void;
}

export default function AnalyzingScreen({
  jobId,
  onSucceeded,
  onFailed,
  onCancel,
}: AnalyzingScreenProps) {
  const [elapsedSec, setElapsedSec] = useState(0);

  const query = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (!status) return 2000;
      return status === "queued" || status === "running" ? 2000 : false;
    },
  });

  const job = query.data;

  // Update document title.
  useEffect(() => {
    if (!job) {
      document.title = "MMR — Analyzing…";
    } else if (job.status === "failed") {
      document.title = `MMR — Failed: ${job.filename}`;
    } else if (job.status === "succeeded") {
      document.title = `MMR — Report: ${job.filename}`;
    } else {
      document.title = `MMR — Analyzing… (${friendlyStage(job.current_stage)})`;
    }
  }, [job]);

  // Tick the elapsed counter once a second.
  useEffect(() => {
    const interval = window.setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => window.clearInterval(interval);
  }, []);

  // Handle terminal states.
  useEffect(() => {
    if (!job) return;
    if (job.status === "succeeded") {
      recordRecentJob({
        id: job.id,
        filename: job.filename,
        completedAt: job.updated_at,
      });
      onSucceeded();
    } else if (job.status === "failed") {
      onFailed();
    }
  }, [job, onSucceeded, onFailed]);

  const cancel = useMutation({
    mutationFn: () => deleteJob(jobId),
    onSuccess: () => onCancel(),
  });

  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col items-center px-4 py-16">
      <div className="w-full rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
        <h2 className="text-lg font-medium text-neutral-900">
          {job?.filename ?? "Analyzing…"}
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Running for {formatElapsed(elapsedSec)}
        </p>

        <div className="mt-6">
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-neutral-100"
            role="progressbar"
            aria-valuenow={Math.round((job?.progress ?? 0) * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            data-testid="progress-bar"
          >
            <div
              className="h-full bg-neutral-900 transition-all duration-500"
              style={{ width: `${Math.max(2, Math.round((job?.progress ?? 0) * 100))}%` }}
            />
          </div>
          <p
            className="mt-3 text-sm text-neutral-700"
            data-testid="stage-label"
          >
            {friendlyStage(job?.current_stage ?? null)}
          </p>
        </div>

        <StageChecklist currentStage={job?.current_stage ?? null} />

        <div className="mt-8 text-right">
          <button
            type="button"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
            className="text-sm text-neutral-500 hover:text-neutral-800 disabled:text-neutral-300"
          >
            Cancel
          </button>
        </div>
      </div>
    </main>
  );
}
