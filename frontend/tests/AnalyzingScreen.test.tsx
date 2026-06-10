import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import AnalyzingScreen from "../src/screens/AnalyzingScreen";
import { renderWithQuery, makeJob } from "./test-utils";
import * as jobsApi from "../src/api/jobs";

describe("AnalyzingScreen", () => {
  it("renders the friendly stage label for the current pipeline stage", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "running", current_stage: "transcribing", progress: 0.4 }),
    );
    renderWithQuery(
      <AnalyzingScreen
        jobId="job-1"
        onSucceeded={() => {}}
        onFailed={() => {}}
        onCancel={() => {}}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("stage-label")).toHaveTextContent("Transcribing speech…");
    });
  });

  it("shows progress percentage on the progress bar", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "running", current_stage: "merging", progress: 0.5 }),
    );
    renderWithQuery(
      <AnalyzingScreen
        jobId="job-2"
        onSucceeded={() => {}}
        onFailed={() => {}}
        onCancel={() => {}}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("progress-bar").getAttribute("aria-valuenow")).toBe("50");
    });
  });

  it("marks earlier stages done, current stage in-progress, later stages pending", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "running", current_stage: "merging" }),
    );
    renderWithQuery(
      <AnalyzingScreen
        jobId="job-3"
        onSucceeded={() => {}}
        onFailed={() => {}}
        onCancel={() => {}}
      />,
    );
    await waitFor(() => {
      const rows = screen
        .getByTestId("stage-checklist")
        .querySelectorAll<HTMLLIElement>("li[data-stage]");
      const find = (stage: string) =>
        Array.from(rows).find((r) => r.dataset.stage === stage);

      expect(find("extracting_frames")?.dataset.state).toBe("done");
      expect(find("transcribing")?.dataset.state).toBe("done");
      expect(find("merging")?.dataset.state).toBe("in_progress");
      expect(find("running_agents")?.dataset.state).toBe("pending");
    });
  });

  it("calls onSucceeded once the job reaches succeeded", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "succeeded", progress: 1.0, updated_at: "2026-06-10T01:00:00Z" }),
    );
    const onSucceeded = vi.fn();
    renderWithQuery(
      <AnalyzingScreen
        jobId="job-4"
        onSucceeded={onSucceeded}
        onFailed={() => {}}
        onCancel={() => {}}
      />,
    );
    await waitFor(() => {
      expect(onSucceeded).toHaveBeenCalled();
    });
  });

  it("calls onFailed when the job ends in failed", async () => {
    vi.spyOn(jobsApi, "getJob").mockResolvedValue(
      makeJob({ status: "failed", error: "extracting_audio: boom" }),
    );
    const onFailed = vi.fn();
    renderWithQuery(
      <AnalyzingScreen
        jobId="job-5"
        onSucceeded={() => {}}
        onFailed={onFailed}
        onCancel={() => {}}
      />,
    );
    await waitFor(() => {
      expect(onFailed).toHaveBeenCalled();
    });
  });
});
