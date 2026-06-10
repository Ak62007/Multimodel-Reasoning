import ReactMarkdown from "react-markdown";
import type { FinalReport } from "../types/api";

interface FinalConclusionProps {
  report: FinalReport;
  onDownload: () => void;
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <section className="mt-8" data-testid={`section-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
      <div className="prose-mmr mt-3 text-sm text-neutral-700">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </section>
  );
}

export default function FinalConclusion({ report, onDownload }: FinalConclusionProps) {
  return (
    <div data-testid="final-conclusion">
      <Section title="Executive Summary" content={report.executive_summary} />
      <Section title="Behavioral Strengths" content={report.behavioral_strengths} />
      <Section
        title="Major Problems & Triggers"
        content={report.vulnerabilities_and_triggers}
      />
      <Section
        title="How to Improve — Actionable Coaching"
        content={report.areas_for_improvement}
      />
      <div className="mt-8">
        <button
          type="button"
          onClick={onDownload}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
          data-testid="download-markdown-bottom"
        >
          Download as Markdown
        </button>
      </div>
    </div>
  );
}
