import React from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, type MemoryRouterProps } from "react-router-dom";

export function renderWithProviders(
  ui: React.ReactElement,
  opts: { route?: string; routerProps?: MemoryRouterProps } & Omit<RenderOptions, "wrapper"> = {},
) {
  const { route = "/", routerProps, ...renderOpts } = opts;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]} {...routerProps}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    ),
    ...renderOpts,
  });
}

export function mockFetch(responses: Array<{ url: RegExp; init?: ResponseInit; body: unknown }>) {
  const original = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : (input as Request).url ?? String(input);
    const match = responses.find((r) => r.url.test(url));
    if (!match) {
      throw new Error(`No fetch mock for ${url}`);
    }
    const body =
      typeof match.body === "string"
        ? match.body
        : JSON.stringify(match.body);
    return new Response(body, match.init ?? { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  return () => {
    globalThis.fetch = original;
  };
}
