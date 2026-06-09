import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { jobsApi } from "../api/jobs";
import type { IntegratedBehavioralReport, ToneLabel } from "../types/api";
import { pushRecentJob, setActiveJobId } from "../lib/storage";
import { formatDuration } from "../lib/time";
import { CrossModalSegment } from "../components/CrossModalSegment";
import { FinalConclusion } from "../components/FinalConclusion";
import { ToneBadge } from "../components/ToneBadge";

export default function ReportScreen() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const jobQ = useQuery({
    queryKey: ["job", id],
    queryFn: () => jobsApi.getJob(id),
    enabled: !!id,
  });

  const segmentsQ = useQuery({
    queryKey: ["segments", id],
    queryFn: () => jobsApi.getSegments(id),
    enabled: jobQ.data?.status === "succeeded",
  });

  const reportQ = useQuery({
    queryKey: ["report", id],
    queryFn: () => jobsApi.getReport(id),
    enabled: jobQ.data?.status === "succeeded",
  });

  const logsQ = useQuery({
    queryKey: ["logs", id, 20],
    queryFn: () => jobsApi.getLogs(id, 20),
    enabled: jobQ.data?.status === "failed",
  });

  useEffect(() => {
    if (jobQ.data?.filename) {
      document.title = `MMR — Report: ${jobQ.data.filename}`;
    }
  }, [jobQ.data?.filename]);

  useEffect(() => {
    if (jobQ.data?.status === "succeeded" && jobQ.data.filename) {
      pushRecentJob({
        id: jobQ.data.id,
        filename: jobQ.data.filename,
        finishedAt: jobQ.data.updated_at,
      });
    }
  }, [jobQ.data]);

  function downloadMarkdown() {
    const md = reportQ.data?.markdown ?? "";
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const fname = jobQ.data?.filename ?? "report";
    a.download = `${fname.replace(/\.[^.]+$/, "")}-behavioral-report.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function newAnalysis() {
    setActiveJobId(null);
    navigate("/");
  }

  if (jobQ.isLoading) {
    return (
      <main className="mx-auto max-w-report px-4 pt-12">
        <ReportSkeleton />
      </main>
    );
  }

  if (!jobQ.data) {
    return (
      <main className="mx-auto max-w-report px-4 pt-12">
        <p className="text-neutral-600">Job not found.</p>
      </main>
    );
  }

  if (jobQ.data.status === "failed") {
    return (
      <main className="mx-auto max-w-report px-4 pt-12 pb-12 space-y-6">
        <section
          className="rounded-lg border-2 border-red-300 bg-red-50 p-6 space-y-3"
          data-testid="error-card"
        >
          <h1 className="text-lg font-semibold text-red-900">Analysis failed</h1>
          <p className="text-sm text-red-800">{jobQ.data.error ?? "Unknown error"}</p>
          <details className="text-xs text-red-700">
            <summary className="cursor-pointer">Show log</summary>
            <pre
              className="mt-2 max-h-64 overflow-auto rounded bg-red-100 p-3 font-mono text-[11px] leading-relaxed"
              data-testid="error-log"
            >
              {logsQ.data?.lines.join("\n") ?? "(log unavailable)"}
            </pre>
          </details>
        </section>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={newAnalysis}
            className="rounded-lg bg-neutral-900 text-white px-4 py-2 text-sm hover:bg-neutral-800"
          >
            Try again
          </button>
          <button
            type="button"
            onClick={async () => {
              await jobsApi.deleteJob(id);
              newAnalysis();
            }}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm hover:bg-neutral-50"
            data-testid="delete-failed-job"
          >
            Delete this job
          </button>
        </div>
      </main>
    );
  }

  if (jobQ.data.status !== "succeeded") {
    return (
      <main className="mx-auto max-w-report px-4 pt-12">
        <p className="text-neutral-600">Job is still {jobQ.data.status}.</p>
      </main>
    );
  }

  const segments = segmentsQ.data?.items ?? [];
  const report = reportQ.data?.structured;
  const totalPatterns = segments.reduce((s, x) => s + x.key_insights.length, 0);
  const overallTone = computeOverallTone(segments);

  return (
    <main className="mx-auto max-w-report px-4 pt-10 pb-16 space-y-10">
      <header className="space-y-3 border-b border-neutral-200 pb-6">
        <div className="text-xs uppercase tracking-wide text-neutral-500">Report</div>
        <h1 className="text-2xl font-semibold" data-testid="report-filename">
          {jobQ.data.filename}
        </h1>
        <div className="text-xs text-neutral-500 flex gap-4">
          <span>Analyzed {new Date(jobQ.data.updated_at).toLocaleString()}</span>
          {jobQ.data.duration_sec != null && (
            <span>Duration {formatDuration(jobQ.data.duration_sec)}</span>
          )}
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={downloadMarkdown}
            className="rounded-lg bg-neutral-900 text-white px-4 py-2 text-sm hover:bg-neutral-800"
            data-testid="download-md"
          >
            Download as Markdown
          </button>
          <button
            type="button"
            onClick={newAnalysis}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm hover:bg-neutral-50"
          >
            New analysis
          </button>
        </div>
      </header>

      {/* Section A — Executive Summary */}
      {report && (
        <section className="space-y-4" data-testid="section-summary">
          <p className="text-base leading-relaxed text-neutral-800">
            {report.executive_summary}
          </p>
          <div className="flex flex-wrap gap-3 text-xs">
            <Chip label="Patterns detected" value={String(totalPatterns)} />
            {overallTone && <Chip label="Overall tone" value={<ToneBadge tone={overallTone} />} />}
          </div>
        </section>
      )}

      {/* Section B — Cross-Modal Patterns */}
      <section className="space-y-4" data-testid="section-patterns">
        <h2 className="text-xl font-semibold border-b border-neutral-200 pb-2">
          Cross-Modal Patterns
        </h2>
        {segments.length === 0 ? (
          <p
            className="rounded-lg border border-neutral-200 bg-neutral-50 p-5 text-sm text-neutral-700"
            data-testid="no-patterns"
          >
            No notable cross-modal patterns detected — the candidate&apos;s behavior,
            voice, and words remained consistent throughout the interview.
          </p>
        ) : (
          <div className="space-y-5">
            {segments.map((s, i) => (
              <CrossModalSegment key={i} segment={s} />
            ))}
          </div>
        )}
      </section>

      {/* Section C — Final Conclusion */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold border-b border-neutral-200 pb-2">
          Final Conclusion
        </h2>
        {report && <FinalConclusion report={report} />}
        <div>
          <button
            type="button"
            onClick={downloadMarkdown}
            className="mt-4 rounded-lg bg-neutral-900 text-white px-4 py-2 text-sm hover:bg-neutral-800"
          >
            Download as Markdown
          </button>
        </div>
      </section>
    </main>
  );
}

function Chip({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1.5 flex items-center gap-2">
      <span className="text-neutral-500">{label}:</span>
      <span className="font-medium text-neutral-900">{value}</span>
    </div>
  );
}

function computeOverallTone(
  segments: IntegratedBehavioralReport[],
): ToneLabel | null {
  if (segments.length === 0) return null;
  const counts = new Map<ToneLabel, number>();
  for (const s of segments) {
    counts.set(s.overall_window_tone, (counts.get(s.overall_window_tone) ?? 0) + 1);
  }
  let best: ToneLabel | null = null;
  let bestN = 0;
  for (const [tone, n] of counts) {
    if (n > bestN) {
      best = tone;
      bestN = n;
    }
  }
  return best;
}

function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 w-2/3 bg-neutral-200 rounded" />
      <div className="h-4 w-1/3 bg-neutral-200 rounded" />
      <div className="h-32 bg-neutral-100 rounded mt-6" />
      <div className="h-32 bg-neutral-100 rounded" />
    </div>
  );
}
