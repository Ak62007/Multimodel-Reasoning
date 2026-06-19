import { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { jobsApi } from "../api/jobs";
import { pushRecentJob, setActiveJobId } from "../lib/storage";
import { formatDuration, parseServerDate } from "../lib/time";
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
    navigate("/upload");
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
        <p className="text-neutral-500">Job not found.</p>
      </main>
    );
  }

  if (jobQ.data.status === "failed") {
    return (
      <main className="mx-auto max-w-report px-4 pt-12 pb-12 space-y-6">
        <section
          className="rounded-2xl border border-rose-400/20 bg-rose-500/[0.06] p-6 space-y-2"
          data-testid="error-card"
        >
          <h1 className="text-lg font-medium text-rose-200">Analysis couldn&apos;t finish</h1>
          <p className="text-sm leading-relaxed text-rose-200/90" data-testid="error-message">
            {jobQ.data.error ?? "Something went wrong. Please try again."}
          </p>
        </section>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={newAnalysis}
            className="rounded-xl bg-sand text-neutral-950 px-4 py-2 text-sm font-semibold transition hover:bg-[#d9c5a3]"
          >
            Try again
          </button>
          <button
            type="button"
            onClick={async () => {
              await jobsApi.deleteJob(id);
              newAnalysis();
            }}
            className="rounded-xl border border-white/10 text-neutral-300 px-4 py-2 text-sm transition hover:border-white/20 hover:bg-white/[0.03]"
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
        <p className="text-neutral-500">Job is still {jobQ.data.status}.</p>
      </main>
    );
  }

  const journal = segmentsQ.data?.items ?? [];
  const report = reportQ.data?.structured;
  const highlights = report?.highlights ?? [];
  const threads = report?.threads ?? [];

  return (
    <main className="mx-auto max-w-report px-4 pt-10 pb-16 space-y-10">
      <header className="space-y-3 border-b border-white/[0.07] pb-6">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-sand/70">
          <span className="h-1.5 w-1.5 rounded-full bg-sand/70" />
          Report
        </div>
        <h1 className="font-display text-3xl font-light text-stone-100" data-testid="report-filename">
          {jobQ.data.filename}
        </h1>
        {report?.headline && (
          <p className="text-base text-neutral-300" data-testid="report-headline">
            {report.headline}
          </p>
        )}
        <div className="flex gap-4 font-mono text-xs text-neutral-500">
          <span>Analyzed {parseServerDate(jobQ.data.updated_at).toLocaleString()}</span>
          {jobQ.data.duration_sec != null && (
            <span>Duration {formatDuration(jobQ.data.duration_sec)}</span>
          )}
          {jobQ.data.total_tokens != null && jobQ.data.total_tokens > 0 && (
            <span data-testid="token-usage">
              {jobQ.data.total_tokens.toLocaleString()} tokens
            </span>
          )}
          {jobQ.data.tier && (
            <span data-testid="tier-label">
              {jobQ.data.tier === "free" ? "Lite (free tier)" : "Full analysis"}
            </span>
          )}
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={downloadMarkdown}
            className="rounded-xl bg-sand text-neutral-950 px-4 py-2 text-sm font-semibold transition hover:bg-[#d9c5a3]"
            data-testid="download-md"
          >
            Download as Markdown
          </button>
          <button
            type="button"
            onClick={newAnalysis}
            className="rounded-xl border border-white/10 text-neutral-300 px-4 py-2 text-sm transition hover:border-white/20 hover:bg-white/[0.03]"
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
        <h2 className="font-display text-2xl font-light text-stone-100 border-b border-white/[0.07] pb-2">
          Highlights — moments worth re-watching
        </h2>
        {highlights.length === 0 ? (
          <p
            className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5 text-sm text-neutral-400"
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
          <h2 className="font-display text-2xl font-light text-stone-100 border-b border-white/[0.07] pb-2">
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
        <h2 className="font-display text-2xl font-light text-stone-100 border-b border-white/[0.07] pb-2">
          Window-by-Window Journal
        </h2>
        {journal.length === 0 ? (
          <p className="text-sm text-neutral-500" data-testid="no-journal">
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
      <h2 className="font-display text-xl font-light text-stone-100">{title}</h2>
      <div className="prose prose-sm prose-invert max-w-none text-[15px] leading-relaxed text-neutral-300 prose-headings:text-neutral-100 prose-strong:text-neutral-100 prose-a:text-sand">
        <ReactMarkdown>{body}</ReactMarkdown>
      </div>
    </article>
  );
}

function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 w-2/3 bg-white/10 rounded" />
      <div className="h-4 w-1/3 bg-white/10 rounded" />
      <div className="h-32 bg-white/[0.04] rounded mt-6" />
      <div className="h-32 bg-white/[0.04] rounded" />
    </div>
  );
}
