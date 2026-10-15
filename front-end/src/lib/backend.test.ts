// @vitest-environment node
import { delay, http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";

import { crawlerApiUrl, crawlPath, DEFAULT_CRAWLER_API_URL, forward } from "./backend";

const API = "http://crawler.test";
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => vi.stubEnv("CRAWLER_API_URL", API));
afterEach(() => {
  server.resetHandlers();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

function dashboardRequest(path: string, init?: RequestInit): Request {
  return new Request(`http://dashboard.test${path}`, init);
}

describe("forward", () => {
  test.each([200, 202, 404, 409, 422])("passes status %i and body through", async (status) => {
    const body = status === 422 ? { detail: [{ loc: ["body"], msg: "bad", type: "x" }] } : { detail: "x" };
    server.use(http.get(`${API}/crawls/1`, () => HttpResponse.json(body, { status })));

    const response = await forward(dashboardRequest("/api/crawls/1"), "/crawls/1");

    expect(response.status).toBe(status);
    expect(await response.json()).toEqual(body);
  });

  test("forwards the query string", async () => {
    let seen = "";
    server.use(
      http.get(`${API}/crawls/1/pages`, ({ request }) => {
        seen = new URL(request.url).search;
        return HttpResponse.json({ total: 0, offset: 20, limit: 10, items: [] });
      }),
    );

    await forward(dashboardRequest("/api/crawls/1/pages?offset=20&limit=10"), "/crawls/1/pages");

    expect(seen).toBe("?offset=20&limit=10");
  });

  test("forwards the method and JSON body", async () => {
    let received: unknown;
    let method = "";
    server.use(
      http.post(`${API}/crawls`, async ({ request }) => {
        method = request.method;
        received = await request.json();
        return HttpResponse.json({ id: "1" }, { status: 202 });
      }),
    );
    const body = { url: "https://example.com/", respect_robots: true };

    const response = await forward(
      dashboardRequest("/api/crawls", { method: "POST", body: JSON.stringify(body) }),
      "/crawls",
    );

    expect(response.status).toBe(202);
    expect(method).toBe("POST");
    expect(received).toEqual(body);
  });

  test("uses the configured crawler API address", async () => {
    vi.stubEnv("CRAWLER_API_URL", "http://crawler:9000/");
    server.use(http.get("http://crawler:9000/crawls", () => HttpResponse.json([])));

    const response = await forward(dashboardRequest("/api/crawls"), "/crawls");

    expect(response.status).toBe(200);
  });

  test("defaults to localhost:8000", () => {
    vi.stubEnv("CRAWLER_API_URL", "");
    expect(crawlerApiUrl()).toBe(DEFAULT_CRAWLER_API_URL);
    expect(DEFAULT_CRAWLER_API_URL).toBe("http://localhost:8000");
  });

  test("reports a refused connection as 502 without revealing the address", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.get(`${API}/crawls`, () => HttpResponse.error()));

    const response = await forward(dashboardRequest("/api/crawls"), "/crawls");

    expect(response.status).toBe(502);
    const body = (await response.json()) as { detail: string };
    expect(body.detail).toBe("Crawler API is unreachable");
    expect(JSON.stringify(body)).not.toContain("crawler.test");
  });

  test("reports a timeout as 502", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(
      http.get(`${API}/crawls`, async () => {
        await delay(500);
        return HttpResponse.json([]);
      }),
    );

    const response = await forward(dashboardRequest("/api/crawls"), "/crawls", { timeoutMs: 20 });

    expect(response.status).toBe(502);
  });
});

test("crawlPath escapes ids", () => {
  expect(crawlPath("a/../b", "/pages")).toBe("/crawls/a%2F..%2Fb/pages");
});
