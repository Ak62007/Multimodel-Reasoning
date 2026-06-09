import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { jobsApi } from "../api/jobs";
import { STAGE_LABELS } from "../types/api";
import { setActiveJobId } from "../lib/storage";
import { formatElapsed } from "../lib/time";
import { StageChecklist } from "../components/StageChecklist";

export default function AnalyzingScreen() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [elapsed, setElapsed] = useState(0);

  const { data: job, error } = useQuery({
    queryKey: ["job", id],
    queryFn: () => jobsApi.getJob(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "succeeded" || s === "failed" ? false : 2000;
    },
    enabled: !!id,
  });

  useEffect(() => {
    document.title = job?.current_stage
      ? `MMR — Analyzing… (${STAGE_LABELS[job.current_stage] ?? job.current_stage})`
      : "MMR — Analyzing…";
  }, [job?.current_stage]);

  useEffect(() => {
    if (!job?.created_at) return;
    const start = new Date(job.created_at).getTime();
    const tick = () => setElapsed(Math.max(0, (Date.now() - start) / 1000));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [job?.created_at]);

  useEffect(() => {
    if (job?.status === "succeeded") navigate(`/report/${id}`);
    if (job?.status === "failed") navigate(`/report/${id}`);
  }, [job?.status, id, navigate]);

  const cancel = useMutation({
    mutationFn: () => jobsApi.deleteJob(id),
    onSuccess: () => {
      setActiveJobId(null);
      toast.success("Analysis cancelled.");
      navigate("/");
    },
    onError: (err: Error) => toast.error(err.message ?? "Could not cancel"),
  });

  if (error) {
    return (
      <main className="mx-auto max-w-xl px-4 pt-16">
        <p className="text-red-600">Failed to load job: {(error as Error).message}</p>
      </main>
    );
  }

  if (!job) return null;

  const friendly = job.current_stage ? STAGE_LABELS[job.current_stage] ?? job.current_stage : "Preparing…";

  return (
    <main className="mx-auto max-w-xl px-4 pt-12 pb-12">
      <section
        className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5"
        data-testid="analyzing-card"
      >
        <header>
          <h2 className="text-xs uppercase tracking-wide text-neutral-500">
            Analyzing
          </h2>
          <h1 className="text-lg font-semibold mt-0.5" data-testid="filename">
            {job.filename}
          </h1>
        </header>

        <div>
          <div className="flex justify-between text-xs text-neutral-600 mb-1.5">
            <span data-testid="stage-label">{friendly}</span>
            <span data-testid="progress-percent">{Math.round(job.progress * 100)}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-neutral-200 overflow-hidden">
            <div
              className="h-full bg-neutral-900 transition-all"
              style={{ width: `${Math.max(2, job.progress * 100)}%` }}
              data-testid="progress-bar"
            />
          </div>
          <div className="mt-2 text-xs text-neutral-500" data-testid="elapsed">
            Running for {formatElapsed(elapsed)}
          </div>
        </div>

        <StageChecklist currentStage={job.current_stage} />

        <button
          type="button"
          onClick={() => cancel.mutate()}
          disabled={cancel.isPending}
          className="w-full rounded-lg border border-neutral-300 text-neutral-700 py-2 text-sm hover:bg-neutral-50 transition"
          data-testid="cancel-button"
        >
          {cancel.isPending ? "Cancelling…" : "Cancel"}
        </button>
      </section>
    </main>
  );
}
