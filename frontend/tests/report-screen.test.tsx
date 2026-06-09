import { describe, it, expect, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ReportScreen from "../src/screens/ReportScreen";
import { mockFetch, renderWithProviders } from "./test-utils";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({ id: "abc" }),
  };
});

type Job = {
  id: string;
  filename: string;
  status: string;
  current_stage: string;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  duration_sec: number;
};

const succeededJob: Job = {
  id: "abc",
  filename: "interview.mp4",
  status: "succeeded",
  current_stage: "generating_final_report",
  progress: 1.0,
  error: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  duration_sec: 124.5,
};

const failedJob: Job = { ...succeededJob, status: "failed", error: "ASR upload failed", progress: 0.2 };

function makeSegment(overrides: Partial<typeof segmentBase> = {}) {
  return { ...segmentBase, ...overrides };
}

const segmentBase = {
  time_range_start: 5,
  time_range_end: 7,
  overall_window_tone: "Mixed_Signals",
  executive_summary: "A short summary of the window.",
  key_insights: [
    {
      timestamp_start: 5.5,
      timestamp_end: 6.0,
      spoken_content: "I worked on the ML stack",
      modalities_involved: ["Visual", "Audio"],
      pattern_type: "Concern",
      significance: "High",
      observation: "Vocal tightening with averted gaze.",
      interpretation: "Possible discomfort with the topic.",
    },
  ],
};

const finalReport = {
  executive_summary: "Solid candidate overall.",
  behavioral_strengths: "Calm and articulate.",
  vulnerabilities_and_triggers: "Stress under deep-technical questions.",
  areas_for_improvement: "Practice technical explanations.",
};

function setupMocks(opts: { job: Job; segments: unknown[]; report?: typeof finalReport }) {
  return mockFetch([
    { url: /\/api\/jobs\/abc$/, body: opts.job },
    { url: /\/api\/jobs\/abc\/segments/, body: { items: opts.segments } },
    {
      url: /\/api\/jobs\/abc\/report/,
      body: { markdown: "# Executive Summary\n\ntest", structured: opts.report ?? finalReport },
    },
    { url: /\/api\/jobs\/abc\/logs/, body: { lines: ["log line 1", "log line 2"] } },
  ]);
}

describe("ReportScreen", () => {
  let restore: () => void;
  afterEach(() => restore?.());

  it("renders all three report sections on success", async () => {
    restore = setupMocks({ job: succeededJob, segments: [makeSegment()] });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getByTestId("section-summary")).toBeInTheDocument());
    expect(screen.getByTestId("section-patterns")).toBeInTheDocument();
    expect(screen.getByTestId("final-conclusion")).toBeInTheDocument();
    // Four sub-sections in Final Conclusion
    expect(screen.getAllByTestId("final-section").length).toBe(4);
    expect(screen.getByTestId("cross-modal-segment")).toBeInTheDocument();
  });

  it("renders the three pattern-type badges with correct colors", async () => {
    restore = setupMocks({
      job: succeededJob,
      segments: [
        makeSegment({
          key_insights: [
            { ...segmentBase.key_insights[0], pattern_type: "Strength" },
            { ...segmentBase.key_insights[0], pattern_type: "Concern" },
            { ...segmentBase.key_insights[0], pattern_type: "Notable" },
          ],
        }),
      ],
    });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getAllByTestId("pattern-type-badge").length).toBe(3));
    const badges = screen.getAllByTestId("pattern-type-badge");
    expect(badges[0].getAttribute("data-type")).toBe("Strength");
    expect(badges[1].getAttribute("data-type")).toBe("Concern");
    expect(badges[2].getAttribute("data-type")).toBe("Notable");
  });

  it("renders the no-patterns fallback when segments is empty", async () => {
    restore = setupMocks({ job: succeededJob, segments: [] });
    renderWithProviders(<ReportScreen />);

    await waitFor(() =>
      expect(screen.getByTestId("no-patterns")).toBeInTheDocument(),
    );
  });

  it("renders the error mode for failed jobs with log tail", async () => {
    restore = setupMocks({ job: failedJob, segments: [] });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getByTestId("error-card")).toBeInTheDocument());
    // The log fetch happens after status flips to "failed"; wait for it.
    await waitFor(() =>
      expect(screen.getByTestId("error-log").textContent).toContain("log line 1"),
    );
  });

  it("Download as Markdown triggers a download", async () => {
    restore = setupMocks({ job: succeededJob, segments: [makeSegment()] });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const createObjectURLSpy = vi.spyOn(URL, "createObjectURL");

    renderWithProviders(<ReportScreen />);
    const btn = await screen.findByTestId("download-md");
    await userEvent.click(btn);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
    createObjectURLSpy.mockRestore();
  });
});
