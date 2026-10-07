// @vitest-environment node
import { readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";

import * as links from "./[id]/links/route";
import * as pages from "./[id]/pages/route";
import * as crawl from "./[id]/route";
import * as status from "./[id]/status/route";
import * as crawls from "./route";

const API = "http://crawler.test";
const server = setupServer();
const seen: string[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  vi.stubEnv("CRAWLER_API_URL", API);
  seen.length = 0;
  server.use(
    http.all(`${API}/*`, ({ request }) => {
      const url = new URL(request.url);
      seen.push(`${request.method} ${url.pathname}${url.search}`);
      return HttpResponse.json({ ok: true });
    }),
  );
});
afterEach(() => {
  server.resetHandlers();
  vi.unstubAllEnvs();
});
afterAll(() => server.close());

const ctx = (id: string) => ({ params: Promise.resolve({ id }) });
const req = (path: string, init?: RequestInit) => new Request(`http://dashboard.test${path}`, init);

describe("each handler forwards to its crawler API operation", () => {
  test("list crawls", async () => {
    await crawls.GET(req("/api/crawls"));
    expect(seen).toEqual(["GET /crawls"]);
  });

  test("start a crawl", async () => {
    await crawls.POST(req("/api/crawls", { method: "POST", body: '{"url":"https://e.com/"}' }));
    expect(seen).toEqual(["POST /crawls"]);
  });

  test("crawl details", async () => {
    await crawl.GET(req("/api/crawls/abc"), ctx("abc"));
    expect(seen).toEqual(["GET /crawls/abc"]);
  });

  test("cancel a crawl", async () => {
    await crawl.DELETE(req("/api/crawls/abc", { method: "DELETE" }), ctx("abc"));
    expect(seen).toEqual(["DELETE /crawls/abc"]);
  });

  test("status", async () => {
    await status.GET(req("/api/crawls/abc/status"), ctx("abc"));
    expect(seen).toEqual(["GET /crawls/abc/status"]);
  });

  test("pages, with paging parameters", async () => {
    await pages.GET(req("/api/crawls/abc/pages?offset=20&limit=10"), ctx("abc"));
    expect(seen).toEqual(["GET /crawls/abc/pages?offset=20&limit=10"]);
  });

  test("links, with paging parameters", async () => {
    await links.GET(req("/api/crawls/abc/links?offset=5&limit=5"), ctx("abc"));
    expect(seen).toEqual(["GET /crawls/abc/links?offset=5&limit=5"]);
  });

  test("ids are escaped", async () => {
    await status.GET(req("/api/crawls/x"), ctx("../health"));
    expect(seen).toEqual(["GET /crawls/..%2Fhealth/status"]);
  });
});

test("only the crawl operations are exposed under /api", () => {
  // Next.js only routes to these files, so any other /api path or method is a 404/405
  // that never reaches the crawler API.
  const apiDir = join(__dirname, "..");
  const routeFiles = (function walk(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
      entry.isDirectory()
        ? walk(join(dir, entry.name))
        : /^route\.[jt]sx?$/.test(entry.name)
          ? [relative(apiDir, join(dir, entry.name)).split(sep).join("/")]
          : [],
    );
  })(apiDir);

  expect(routeFiles.sort()).toEqual([
    "crawls/[id]/links/route.ts",
    "crawls/[id]/pages/route.ts",
    "crawls/[id]/route.ts",
    "crawls/[id]/status/route.ts",
    "crawls/route.ts",
  ]);
  expect(Object.keys(crawls).sort()).toEqual(["GET", "POST"]);
  expect(Object.keys(crawl).sort()).toEqual(["DELETE", "GET"]);
  for (const handlers of [status, pages, links]) {
    expect(Object.keys(handlers)).toEqual(["GET"]);
  }
});
