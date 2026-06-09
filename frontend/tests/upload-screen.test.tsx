import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UploadScreen from "../src/screens/UploadScreen";
import { mockFetch, renderWithProviders } from "./test-utils";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

describe("UploadScreen", () => {
  let restore: () => void;

  beforeEach(() => {
    navigateMock.mockReset();
    restore = mockFetch([
      {
        url: /\/api\/jobs$/,
        init: { status: 201, headers: { "Content-Type": "application/json" } },
        body: {
          id: "abc123",
          filename: "interview.mp4",
          status: "queued",
          current_stage: null,
          progress: 0,
          error: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          duration_sec: null,
        },
      },
    ]);
  });

  afterEach(() => restore());

  it("disables Start Analysis until a file is selected", () => {
    renderWithProviders(<UploadScreen />);
    const btn = screen.getByTestId("start-button") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("enables submit and navigates to the analyzing screen on upload", async () => {
    renderWithProviders(<UploadScreen />);
    const file = new File(["x"], "interview.mp4", { type: "video/mp4" });
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    const btn = await screen.findByTestId("start-button");
    await userEvent.click(btn);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/analyzing/abc123"));
    expect(localStorage.getItem("mmr:active-job-id")).toBe("abc123");
  });
});
