import { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

export function renderWithQuery(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

export function makeJob(overrides: Partial<{
  id: string;
  filename: string;
  status: "queued" | "running" | "succeeded" | "failed";
  current_stage: string | null;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  duration_sec: number | null;
}> = {}) {
  return {
    id: "job-1",
    filename: "interview.mp4",
    status: "running" as const,
    current_stage: null,
    progress: 0,
    error: null,
    created_at: "2026-06-10T00:00:00Z",
    updated_at: "2026-06-10T00:00:00Z",
    duration_sec: null,
    ...overrides,
  };
}
