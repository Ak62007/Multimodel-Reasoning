import { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { jobsApi } from "../api/jobs";
import { pushRecentJob, setActiveJobId } from "../lib/storage";
import { formatDuration } from "../lib/time";
import { HighlightCard } from "../components/HighlightCard";
import { ThreadCard } from "../components/ThreadCard";
import { WindowNote } from "../components/WindowNote";

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

  const journal = segmentsQ.data?.items ?? [];
  const report = reportQ.data?.structured;
  const highlights = report?.highlights ?? [];
  const threads = report?.threads ?? [];

  return (
    <main className="mx-auto max-w-report px-4 pt-10 pb-16 space-y-10">
      <header className="space-y-3 border-b border-neutral-200 pb-6">
        <div className="text-xs uppercase tracking-wide text-neutral-500">Report</div>
        <h1 className="text-2xl font-semibold" data-testid="report-filename">
          {jobQ.data.filename}
        </h1>
        {report?.headline && (
          <p className="text-base text-neutral-800" data-testid="report-headline">
            {report.headline}
          </p>
        )}
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

      {/* Section A — Overview + Behavioral arc */}
      {report && (
        <section className="space-y-6" data-testid="section-summary">
          <Prose title="Overview" body={report.overview} />
          <Prose title="Behavioral Arc" body={report.behavioral_arc} />
        </section>
      )}

      {/* Section B — Highlights (the hero: jump-back-to-the-video list) */}
      <section className="space-y-4" data-testid="section-highlights">
        <h2 className="text-xl font-semibold border-b border-neutral-200 pb-2">
          Highlights — moments worth re-watching
        </h2>
        {highlights.length === 0 ? (
          <p
            className="rounded-lg border border-neutral-200 bg-neutral-50 p-5 text-sm text-neutral-700"
            data-testid="no-highlights"
          >
            No standout moments surfaced — the candidate&apos;s behavior, voice, and
            words stayed consistent throughout.
          </p>
        ) : (
          <div className="space-y-4">
            {highlights.map((h, i) => (
              <HighlightCard key={i} highlight={h} />
            ))}
          </div>
        )}
      </section>

      {/* Section C — Recurring threads */}
      {threads.length > 0 && (
        <section className="space-y-4" data-testid="section-threads">
          <h2 className="text-xl font-semibold border-b border-neutral-200 pb-2">
            Recurring Threads
          </h2>
          <div className="space-y-4">
            {threads.map((t, i) => (
              <ThreadCard key={i} thread={t} />
            ))}
          </div>
        </section>
      )}

      {/* Section D — Window-by-window journal */}
      <section className="space-y-4" data-testid="section-journal">
        <h2 className="text-xl font-semibold border-b border-neutral-200 pb-2">
          Window-by-Window Journal
        </h2>
        {journal.length === 0 ? (
          <p className="text-sm text-neutral-600" data-testid="no-journal">
            No analysis windows were produced for this interview.
          </p>
        ) : (
          <div className="space-y-3">
            {journal.map((note, i) => (
              <WindowNote key={i} note={note} />
            ))}
          </div>
        )}
      </section>

      {/* Section E — Coaching notes */}
      {report?.coaching_notes && (
        <section className="space-y-4" data-testid="section-coaching">
          <Prose title="Coaching Notes" body={report.coaching_notes} />
        </section>
      )}
    </main>
  );
}

function Prose({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <article className="space-y-2" data-testid="prose-section">
      <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
      <div className="prose prose-sm max-w-none text-neutral-800">
        <ReactMarkdown>{body}</ReactMarkdown>
      </div>
    </article>
  );
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
