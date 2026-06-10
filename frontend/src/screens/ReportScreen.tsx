import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getJob, getLogs, getReport, getSegments } from "../api/jobs";
import { formatMMSS } from "../lib/time";
import type { IntegratedBehavioralReport, WindowTone } from "../types/api";
import CrossModalSegment from "../components/CrossModalSegment";
import FinalConclusion from "../components/FinalConclusion";
import ToneBadge from "../components/ToneBadge";

interface ReportScreenProps {
  jobId: string;
  onNewAnalysis: () => void;
}

function modalTone(segments: IntegratedBehavioralReport[]): WindowTone {
  if (segments.length === 0) return "Authentic";
  const counts = new Map<WindowTone, number>();
  for (const s of segments) {
    counts.set(s.overall_window_tone, (counts.get(s.overall_window_tone) ?? 0) + 1);
  }
  let best: WindowTone = "Authentic";
  let bestCount = -1;
  for (const [tone, count] of counts.entries()) {
    if (count > bestCount) {
      best = tone;
      bestCount = count;
    }
  }
  return best;
}

function totalInsights(segments: IntegratedBehavioralReport[]): number {
  return segments.reduce((acc, s) => acc + s.key_insights.length, 0);
}

function totalDurationSec(segments: IntegratedBehavioralReport[]): number {
  if (segments.length === 0) return 0;
  let max = 0;
  for (const s of segments) {
    if (s.time_range_end > max) max = s.time_range_end;
  }
  return max;
}

export default function ReportScreen({ jobId, onNewAnalysis }: ReportScreenProps) {
  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
  });
  const job = jobQuery.data;

  const failed = job?.status === "failed";

  const segmentsQuery = useQuery({
    queryKey: ["segments", jobId],
    queryFn: () => getSegments(jobId),
    enabled: !!job && job.status === "succeeded",
  });

  const reportQuery = useQuery({
    queryKey: ["report", jobId],
    queryFn: () => getReport(jobId),
    enabled: !!job && job.status === "succeeded",
  });

  const logsQuery = useQuery({
    queryKey: ["logs", jobId],
    queryFn: () => getLogs(jobId, 20),
    enabled: failed,
  });

  const segments = useMemo(
    () => segmentsQuery.data ?? [],
    [segmentsQuery.data],
  );
  const report = reportQuery.data;

  useEffect(() => {
    if (job) {
      document.title = `MMR — Report: ${job.filename}`;
    } else {
      document.title = "MMR — Report";
    }
  }, [job]);

  const tone = useMemo(() => modalTone(segments), [segments]);
  const insightsCount = useMemo(() => totalInsights(segments), [segments]);
  const durationSec = useMemo(() => totalDurationSec(segments), [segments]);

  function handleDownload() {
    if (!report) return;
    const filename = (job?.filename ?? "report").replace(/\.[^.]+$/, "");
    const blob = new Blob([report.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}-behavioral-report.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  if (failed && job) {
    return (
      <main className="mx-auto flex min-h-screen max-w-reading flex-col px-4 py-12">
        <div className="rounded-lg border-2 border-red-200 bg-white p-6 shadow-sm" data-testid="error-card">
          <h1 className="text-xl font-semibold text-red-700">Analysis failed</h1>
          <p className="mt-2 text-sm text-neutral-700">{job.error}</p>
          {logsQuery.data && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-neutral-500">Show log</summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-neutral-50 p-3 text-xs text-neutral-700">
                {logsQuery.data.lines.join("\n")}
              </pre>
            </details>
          )}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={onNewAnalysis}
              className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white"
            >
              Try again
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (!job || !report) {
    return (
      <main className="mx-auto flex min-h-screen max-w-reading items-center justify-center px-4">
        <p className="text-sm text-neutral-500">Loading report…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-reading px-4 py-12">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">{job.filename}</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Analyzed {new Date(job.updated_at).toLocaleString()}
            {job.duration_sec ? ` · ${Math.round(job.duration_sec)}s` : null}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleDownload}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
            data-testid="download-markdown-top"
          >
            Download as Markdown
          </button>
          <button
            type="button"
            onClick={onNewAnalysis}
            className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-neutral-800"
            data-testid="new-analysis"
          >
            New analysis
          </button>
        </div>
      </header>

      {/* Section A — Executive Summary */}
      <section className="mt-8 rounded-lg border border-neutral-200 bg-white p-5 shadow-sm" data-testid="section-executive">
        <h2 className="text-lg font-semibold text-neutral-900">Executive Summary</h2>
        <p className="mt-3 text-sm text-neutral-700">{report.structured.executive_summary}</p>
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-neutral-700">
          <div className="rounded-md border border-neutral-200 px-3 py-1.5" data-testid="stat-duration">
            Total duration · <strong>{formatMMSS(durationSec)}</strong>
          </div>
          <div className="rounded-md border border-neutral-200 px-3 py-1.5" data-testid="stat-patterns">
            Patterns detected · <strong>{insightsCount}</strong>
          </div>
          <div className="rounded-md border border-neutral-200 px-3 py-1.5" data-testid="stat-tone">
            Overall tone · <ToneBadge tone={tone} />
          </div>
        </div>
      </section>

      {/* Section B — Cross-Modal Patterns */}
      <section className="mt-10" data-testid="section-patterns">
        <h2 className="text-lg font-semibold text-neutral-900">Cross-Modal Patterns</h2>
        {segments.length === 0 ? (
          <p
            className="mt-4 rounded-lg border border-neutral-200 bg-white p-5 text-sm text-neutral-600 shadow-sm"
            data-testid="patterns-empty"
          >
            No notable cross-modal patterns detected — the candidate's behavior, voice, and words
            remained consistent throughout the interview.
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {segments.map((segment, i) => (
              <CrossModalSegment key={i} report={segment} />
            ))}
          </div>
        )}
      </section>

      {/* Section C — Final Conclusion */}
      <section className="mt-10" data-testid="section-final">
        <h2 className="text-lg font-semibold text-neutral-900">Final Conclusion</h2>
        <FinalConclusion report={report.structured} onDownload={handleDownload} />
      </section>
    </main>
  );
}
