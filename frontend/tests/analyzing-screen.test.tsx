import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import AnalyzingScreen from "../src/screens/AnalyzingScreen";
import { mockFetch, renderWithProviders } from "./test-utils";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn(), useParams: () => ({ id: "abc" }) };
});

function jobRunning(stage: string, progress: number) {
  return {
    id: "abc",
    filename: "interview.mp4",
    status: "running",
    current_stage: stage,
    progress,
    error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    duration_sec: null,
  };
}

describe("AnalyzingScreen", () => {
  let restore: () => void;
  afterEach(() => restore?.());

  beforeEach(() => {
    restore = mockFetch([
      {
        url: /\/api\/jobs\/abc$/,
        body: jobRunning("extracting_face_features", 0.3),
      },
    ]);
  });

  it("renders the friendly stage label and progress", async () => {
    renderWithProviders(<AnalyzingScreen />);
    await waitFor(() => expect(screen.getByTestId("stage-label")).toHaveTextContent("facial"));
    expect(screen.getByTestId("progress-percent")).toHaveTextContent("30%");
  });

  it("StageChecklist marks earlier stages as done and current as active", async () => {
    renderWithProviders(<AnalyzingScreen />);
    await waitFor(() =>
      expect(
        screen.getByTestId("stage-extracting_face_features").getAttribute("data-state"),
      ).toBe("active"),
    );
    expect(
      screen.getByTestId("stage-extracting_audio").getAttribute("data-state"),
    ).toBe("done");
    expect(
      screen.getByTestId("stage-running_agents").getAttribute("data-state"),
    ).toBe("pending");
  });
});
