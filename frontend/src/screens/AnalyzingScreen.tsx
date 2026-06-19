import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { jobsApi } from "../api/jobs";
import { STAGE_BLURBS, STAGE_LABELS } from "../types/api";
import { setActiveJobId } from "../lib/storage";
import { formatElapsed, parseServerDate } from "../lib/time";
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
    const start = parseServerDate(job.created_at).getTime();
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
      navigate("/upload");
    },
    onError: (err: Error) => toast.error(err.message ?? "Could not cancel"),
  });

  if (error) {
    return (
      <main className="mx-auto max-w-xl px-4 pt-16">
        <p className="text-rose-300">Failed to load job: {(error as Error).message}</p>
      </main>
    );
  }

  if (!job) return null;

  const friendly = job.current_stage ? STAGE_LABELS[job.current_stage] ?? job.current_stage : "Preparing…";
  const blurb = job.current_stage ? STAGE_BLURBS[job.current_stage] : null;

  return (
    <main className="mx-auto max-w-xl px-4 pt-16 pb-12">
      <section
        className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-6 space-y-6"
        data-testid="analyzing-card"
      >
        <header>
          <h2 className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-sand/80">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-sand" />
            Analyzing
          </h2>
          <h1 className="mt-2 text-lg font-medium text-neutral-100" data-testid="filename">
            {job.filename}
          </h1>
        </header>

        <div>
          <div className="flex justify-between text-xs text-neutral-400 mb-2">
            <span data-testid="stage-label">{friendly}</span>
            <span className="font-mono text-neutral-500" data-testid="progress-percent">
              {Math.round(job.progress * 100)}%
            </span>
          </div>
          <div className="w-full h-1 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full bg-sand transition-all duration-500"
              style={{ width: `${Math.max(2, job.progress * 100)}%` }}
              data-testid="progress-bar"
            />
          </div>
          <div className="mt-2 font-mono text-xs text-neutral-500" data-testid="elapsed">
            Running for {formatElapsed(elapsed)}
          </div>
        </div>

        {blurb && (
          <p
            className="rounded-xl border border-sand/15 bg-sand/[0.04] px-4 py-3 text-sm leading-relaxed text-stone-300"
            data-testid="stage-blurb"
          >
            {blurb}
          </p>
        )}

        <StageChecklist currentStage={job.current_stage} />

        <button
          type="button"
          onClick={() => cancel.mutate()}
          disabled={cancel.isPending}
          className="w-full rounded-xl border border-white/10 text-neutral-300 py-2 text-sm transition hover:border-white/20 hover:bg-white/[0.03]"
          data-testid="cancel-button"
        >
          {cancel.isPending ? "Cancelling…" : "Cancel"}
        </button>
      </section>
    </main>
  );
}
