import { describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import ReportScreen from "../src/screens/ReportScreen";
import { renderWithQuery, makeJob } from "./test-utils";
import * as jobsApi from "../src/api/jobs";
import type { FinalReport, IntegratedBehavioralReport } from "../src/types/api";

function mockSucceeded(
  segments: IntegratedBehavioralReport[],
  finalReport: Partial<FinalReport> = {},
) {
  vi.spyOn(jobsApi, "getJob").mockResolvedValue(
    makeJob({
      status: "succeeded",
      progress: 1,
      filename: "interview.mp4",
      updated_at: "2026-06-10T01:00:00Z",
      duration_sec: 30,
    }),
  );
  vi.spyOn(jobsApi, "getSegments").mockResolvedValue(segments);
  vi.spyOn(jobsApi, "getReport").mockResolvedValue({
    markdown: "# Executive Summary\n\nThe candidate did fine.\n",
    structured: {
      executive_summary: "The candidate did fine.",
      behavioral_strengths: "- Steady tone.",
      vulnerabilities_and_triggers: "- None significant.",
      areas_for_improvement: "1. Take more pauses.",
      ...finalReport,
    },
  });
}

const exampleSegment: IntegratedBehavioralReport = {
  time_range_start: 5,
  time_range_end: 7,
  overall_window_tone: "Mixed_Signals",
  executive_summary: "Brief tension while talking about ML.",
  key_insights: [
    {
      timestamp_start: 5,
      timestamp_end: 7,
      spoken_content: "I have a lot of experience.",
      modalities_involved: ["Visual", "Audio"],
      pattern_type: "Concern",
      significance: "Medium",
      observation: "Pitch tightened and blinks spiked.",
      interpretation: "Possible overclaim regarding ML experience.",
    },
  ],
};

describe("ReportScreen", () => {
  it("renders all three sections when segments + report are present", async () => {
    mockSucceeded([exampleSegment]);
    renderWithQuery(<ReportScreen jobId="job-1" onNewAnalysis={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("section-executive")).toBeInTheDocument();
      expect(screen.getByTestId("section-patterns")).toBeInTheDocument();
      expect(screen.getByTestId("section-final")).toBeInTheDocument();
    });
  });

  it("renders the no-patterns fallback message when segments is []", async () => {
    mockSucceeded([]);
    renderWithQuery(<ReportScreen jobId="job-2" onNewAnalysis={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("patterns-empty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("patterns-empty")).toHaveTextContent(
      /no notable cross-modal patterns detected/i,
    );
  });

  it("colors pattern badges correctly for Strength / Concern / Notable", async () => {
    const strengthInsight: IntegratedBehavioralReport = {
      time_range_start: 0,
      time_range_end: 1,
      overall_window_tone: "Strong_Positive",
      executive_summary: "x",
      key_insights: [
        { ...exampleSegment.key_insights[0], pattern_type: "Strength" },
      ],
    };
    const concernInsight: IntegratedBehavioralReport = {
      ...strengthInsight,
      time_range_start: 1,
      time_range_end: 2,
      key_insights: [{ ...exampleSegment.key_insights[0], pattern_type: "Concern" }],
    };
    const notableInsight: IntegratedBehavioralReport = {
      ...strengthInsight,
      time_range_start: 2,
      time_range_end: 3,
      key_insights: [{ ...exampleSegment.key_insights[0], pattern_type: "Notable" }],
    };
    mockSucceeded([strengthInsight, concernInsight, notableInsight]);
    renderWithQuery(<ReportScreen jobId="job-colors" onNewAnalysis={() => {}} />);
    await waitFor(() => {
      const badges = screen.getAllByTestId("pattern-type-badge");
      const colors = badges.map((b) => b.getAttribute("data-color"));
      expect(colors).toEqual(expect.arrayContaining(["green", "red", "amber"]));
    });
  });

  it("downloads the report markdown when the button is clicked", async () => {
    const createObjectURL = vi.fn().mockReturnValue("blob:fake");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { value: createObjectURL, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeObjectURL, configurable: true });

    mockSucceeded([exampleSegment]);
    renderWithQuery(<ReportScreen jobId="job-dl" onNewAnalysis={() => {}} />);
    const button = await screen.findByTestId("download-markdown-top");
    const clickedLinks: { href?: string; download?: string }[] = [];
    const origAppend = document.body.appendChild;
    vi.spyOn(document.body, "appendChild").mockImplementation((node) => {
      if (node instanceof HTMLAnchorElement) {
        clickedLinks.push({ href: node.href, download: node.download });
      }
      return origAppend.call(document.body, node);
    });

    fireEvent.click(button);
    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(clickedLinks[0]?.download).toBe("interview-behavioral-report.md");
  });

  it("renders an error card with the log tail when the job failed", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "failed", error: "extracting_audio: boom" }),
    );
    vi.spyOn(jobsApi, "getLogs").mockResolvedValue({
      lines: ["log line 1", "log line 2"],
    });
    renderWithQuery(<ReportScreen jobId="job-fail" onNewAnalysis={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("error-card")).toBeInTheDocument();
    });
    expect(screen.getByText(/extracting_audio: boom/)).toBeInTheDocument();
    // The logs <details> only renders after logsQuery resolves.
    const showLogButton = await screen.findByText("Show log");
    fireEvent.click(showLogButton);
    await waitFor(() => {
      expect(screen.getByText(/log line 1/)).toBeInTheDocument();
    });
  });
});
