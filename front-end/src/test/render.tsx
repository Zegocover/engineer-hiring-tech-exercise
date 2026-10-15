import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { setupServer } from "msw/node";
import type { ReactElement } from "react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { makeQueryClient } from "@/app/providers";
import { polling } from "@/lib/polling";

import { FakeApi } from "./fakeApi";

/** Renders ``ui`` with a fresh QueryClient using the app's retry policy, minus retry delays. */
export function renderWithClient(ui: ReactElement): ReturnType<typeof render> & { client: QueryClient } {
  const client = makeQueryClient();
  const defaults = client.getDefaultOptions();
  client.setDefaultOptions({ ...defaults, queries: { ...defaults.queries, retryDelay: 0 } });
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}

/**
 * Serves a fresh FakeApi for every test in the calling file and shortens polling.
 * Returns a getter for the current test's fake.
 */
export function serveFakeApi(): () => FakeApi {
  const server = setupServer();
  const saved = { ...polling };
  let api = new FakeApi();

  beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
  beforeEach(() => {
    api = new FakeApi();
    server.use(...api.handlers());
    Object.assign(polling, { listMs: 20, statusMs: 20, resultsMs: 20 });
  });
  afterEach(() => {
    server.resetHandlers();
    Object.assign(polling, saved);
  });
  afterAll(() => server.close());

  return () => api;
}
