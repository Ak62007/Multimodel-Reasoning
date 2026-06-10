import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import UploadScreen from "../src/screens/UploadScreen";
import { renderWithQuery, makeJob } from "./test-utils";
import * as jobsApi from "../src/api/jobs";

describe("UploadScreen", () => {
  beforeEach(() => {
    vi.spyOn(jobsApi, "uploadJob").mockResolvedValue(makeJob({ status: "queued" }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("disables Start Analysis until a file is selected", () => {
    renderWithQuery(
      <UploadScreen onJobCreated={() => {}} onViewRecent={() => {}} />,
    );
    const button = screen.getByTestId("start-analysis") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("selecting a file enables Start Analysis", async () => {
    renderWithQuery(
      <UploadScreen onJobCreated={() => {}} onViewRecent={() => {}} />,
    );
    const file = new File(["x"], "test.mp4", { type: "video/mp4" });
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect((screen.getByTestId("start-analysis") as HTMLButtonElement).disabled).toBe(false);
    });
    expect(screen.getByText("test.mp4")).toBeInTheDocument();
  });

  it("submitting the form calls uploadJob and onJobCreated with the new id", async () => {
    const onJobCreated = vi.fn();
    renderWithQuery(
      <UploadScreen onJobCreated={onJobCreated} onViewRecent={() => {}} />,
    );
    const file = new File(["x"], "interview.mp4", { type: "video/mp4" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    fireEvent.click(screen.getByTestId("start-analysis"));

    await waitFor(() => {
      expect(jobsApi.uploadJob).toHaveBeenCalledWith(file, "B");
    });
    await waitFor(() => {
      expect(onJobCreated).toHaveBeenCalledWith("job-1");
    });
  });

  it("renders the advanced toggle for speaker label", async () => {
    renderWithQuery(
      <UploadScreen onJobCreated={() => {}} onViewRecent={() => {}} />,
    );
    fireEvent.click(screen.getByText("Advanced"));
    const input = (await screen.findByLabelText("Speaker label")) as HTMLInputElement;
    expect(input.value).toBe("B");
    fireEvent.change(input, { target: { value: "a" } });
    expect(input.value).toBe("A");
  });
});
