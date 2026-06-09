import ReactMarkdown from "react-markdown";
import type { FinalReport } from "../types/api";

export function FinalConclusion({ report }: { report: FinalReport }) {
  return (
    <section className="space-y-8" data-testid="final-conclusion">
      <Section title="Executive Summary" body={report.executive_summary} />
      <Section title="Behavioral Strengths" body={report.behavioral_strengths} />
      <Section title="Major Problems & Triggers" body={report.vulnerabilities_and_triggers} />
      <Section title="How to Improve — Actionable Coaching" body={report.areas_for_improvement} />
    </section>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <article className="space-y-2" data-testid="final-section">
      <h2 className="text-lg font-semibold text-neutral-900 border-b border-neutral-200 pb-2">
        {title}
      </h2>
      <div className="prose prose-sm max-w-none text-neutral-800">
        <ReactMarkdown>{body}</ReactMarkdown>
      </div>
    </article>
  );
}
