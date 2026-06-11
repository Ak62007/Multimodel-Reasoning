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

const windowNote = {
  time_start: 5,
  time_end: 7,
  phase: "Early",
  position_pct: 0.1,
  spoken_excerpt: "I worked on the ML stack",
  visual_read: "Steady gaze.",
  audio_read: "Voice tightened.",
  verbal_read: "Fluent.",
  narrative: "A vocal tightening stands out on the ML claim.",
  window_interest: "High",
  signals: [
    {
      timestamp_start: 5.5,
      timestamp_end: 6.0,
      modalities: ["Audio", "Verbal"],
      relation: "Contradiction",
      kind: "Tell",
      headline: "Voice tightened on a claim",
      evidence: "Pitch rose while claiming ownership.",
      spoken_content: "I worked on the ML stack",
      interpretation: "Possible discomfort with the topic.",
      significance: "High",
    },
  ],
};

const finalReport = {
  headline: "Composed but tense on ownership claims.",
  overview: "Solid candidate overall.",
  behavioral_arc: "Calm open, tense middle, recovery by close.",
  highlights: [
    {
      ts_start: 5.5,
      ts_end: 6.0,
      title: "Voice tightened on a claim",
      what_happened: "Pitch rose while claiming ownership.",
      why_it_matters: "Worth probing the claim.",
      modalities: ["Audio", "Verbal"],
      kind: "Tell",
      significance: "High",
    },
  ],
  threads: [
    {
      title: "Tension on ownership claims",
      summary: "Voice tightens whenever credit is claimed.",
      relation: "Contradiction",
      occurrences: [5.5, 88.0],
      interpretation: "A consistent tell around credit.",
    },
  ],
  coaching_notes: "Practice claims aloud.",
};

function setupMocks(opts: { job: Job; segments: unknown[]; report?: typeof finalReport }) {
  return mockFetch([
    { url: /\/api\/jobs\/abc$/, body: opts.job },
    { url: /\/api\/jobs\/abc\/segments/, body: { items: opts.segments } },
    {
      url: /\/api\/jobs\/abc\/report/,
      body: { markdown: "# Composed\n\ntest", structured: opts.report ?? finalReport },
    },
    { url: /\/api\/jobs\/abc\/logs/, body: { lines: ["log line 1", "log line 2"] } },
  ]);
}

describe("ReportScreen", () => {
  let restore: () => void;
  afterEach(() => restore?.());

  it("renders overview, highlights, threads, and journal on success", async () => {
    restore = setupMocks({ job: succeededJob, segments: [windowNote] });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getByTestId("section-summary")).toBeInTheDocument());
    expect(screen.getByTestId("report-headline")).toHaveTextContent("ownership claims");
    expect(screen.getByTestId("section-highlights")).toBeInTheDocument();
    expect(screen.getByTestId("highlight-card")).toBeInTheDocument();
    expect(screen.getByTestId("section-threads")).toBeInTheDocument();
    expect(screen.getByTestId("thread-card")).toBeInTheDocument();
    expect(screen.getByTestId("section-journal")).toBeInTheDocument();
    expect(screen.getByTestId("window-note")).toBeInTheDocument();
  });

  it("renders kind badges with the correct kind attribute", async () => {
    restore = setupMocks({
      job: succeededJob,
      segments: [windowNote],
      report: {
        ...finalReport,
        highlights: [
          { ...finalReport.highlights[0], kind: "Strength" },
          { ...finalReport.highlights[0], kind: "Tension" },
          { ...finalReport.highlights[0], kind: "Quirk" },
        ],
      },
    });
    renderWithProviders(<ReportScreen />);

    await waitFor(() =>
      expect(screen.getAllByTestId("highlight-card").length).toBe(3),
    );
    const badges = screen
      .getAllByTestId("highlight-card")
      .map((card) => card.querySelector('[data-testid="kind-badge"]')?.getAttribute("data-kind"));
    expect(badges).toEqual(["Strength", "Tension", "Quirk"]);
  });

  it("renders the no-highlights fallback when there are none", async () => {
    restore = setupMocks({
      job: succeededJob,
      segments: [],
      report: { ...finalReport, highlights: [], threads: [] },
    });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getByTestId("no-highlights")).toBeInTheDocument());
  });

  it("renders the error mode for failed jobs with log tail", async () => {
    restore = setupMocks({ job: failedJob, segments: [] });
    renderWithProviders(<ReportScreen />);

    await waitFor(() => expect(screen.getByTestId("error-card")).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByTestId("error-log").textContent).toContain("log line 1"),
    );
  });

  it("Download as Markdown triggers a download", async () => {
    restore = setupMocks({ job: succeededJob, segments: [windowNote] });
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
