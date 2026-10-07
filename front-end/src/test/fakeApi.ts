// An in-memory stand-in for the dashboard's /api routes, served by MSW in component tests.
// Tests mutate its state (advance a crawl, take the API down) and inspect the requests made.
import { http, type HttpHandler, HttpResponse } from "msw";

import type {
  CrawlDetail,
  CrawlRequest,
  CrawlStatus,
  CrawlSummary,
  JobStatus,
  ValidationError,
} from "@/lib/api/types";

export type FakeCrawl = { detail: CrawlDetail; pageUrls: string[]; links: string[] };

let counter = 0;

function pageUrlsFor(url: string, pages: number): string[] {
  return Array.from({ length: pages }, (_, i) => (i === 0 ? url : `${url}${i}`));
}

export function makeCrawl(overrides: Partial<CrawlDetail> = {}, pages = 0): FakeCrawl {
  counter += 1;
  const url = overrides.url ?? "https://example.com/";
  const pageUrls = pageUrlsFor(url, pages);
  return {
    detail: {
      id: `crawl-${counter}`,
      url,
      status: "completed",
      started_at: "2026-10-07T10:00:00Z",
      finished_at: "2026-10-07T10:00:05Z",
      stats: { pages, fetched: pages, errors: 0, robots_skipped: 0 },
      limits: {
        max_pages: 1000,
        max_depth: null,
        concurrency: 8,
        per_host_concurrency: null,
        respect_robots: true,
        allowed_hosts: [],
      },
      error: null,
      ...overrides,
    },
    pageUrls,
    links: pageUrls.slice(1),
  };
}

function summaryOf(d: CrawlDetail): CrawlSummary {
  return {
    id: d.id,
    url: d.url,
    status: d.status,
    started_at: d.started_at,
    finished_at: d.finished_at,
    stats: d.stats,
  };
}

function statusOf(d: CrawlDetail): CrawlStatus {
  return {
    id: d.id,
    status: d.status,
    started_at: d.started_at,
    finished_at: d.finished_at,
    stats: d.stats,
    error: d.error,
  };
}

function paging(request: Request): { offset: number; limit: number } {
  const params = new URL(request.url).searchParams;
  return { offset: Number(params.get("offset") ?? 0), limit: Number(params.get("limit") ?? 100) };
}

function notFound(id: string) {
  return HttpResponse.json({ detail: `crawl ${id} not found` }, { status: 404 });
}

export class FakeApi {
  /** Crawls in the order they were started (newest last). */
  crawls: FakeCrawl[] = [];
  /** Every request received, as "METHOD /path?query". */
  requests: string[] = [];
  /** When set, every request fails with this status (502 = crawler API unreachable). */
  failWith: number | null = null;
  /** When set, POST /api/crawls responds 422 with these errors. */
  rejectStart: ValidationError[] | null = null;
  /** When set, DELETE first finishes the crawl with this status, then responds 409. */
  cancelLoses: JobStatus | null = null;
  /** Bodies of start requests received. */
  started: CrawlRequest[] = [];
  /** When set, POST /api/crawls waits for this promise before answering. */
  holdStart: Promise<void> | null = null;

  add(...crawls: FakeCrawl[]): this {
    this.crawls.push(...crawls);
    return this;
  }

  get(id: string): FakeCrawl | undefined {
    return this.crawls.find((c) => c.detail.id === id);
  }

  /** Make a crawl report ``pages`` pages, as a running crawl would. */
  progress(id: string, pages: number): void {
    const crawl = this.get(id)!;
    crawl.pageUrls = pageUrlsFor(crawl.detail.url, pages);
    crawl.links = crawl.pageUrls.slice(1);
    crawl.detail.stats = { ...crawl.detail.stats, pages, fetched: pages };
  }

  finish(id: string, status: JobStatus = "completed", error: string | null = null): void {
    const detail = this.get(id)!.detail;
    detail.status = status;
    detail.finished_at = "2026-10-07T10:01:00Z";
    detail.error = error;
  }

  /** Number of requests whose "METHOD /path" starts with ``prefix``. */
  count(prefix: string): number {
    return this.requests.filter((r) => r.startsWith(prefix)).length;
  }

  handlers(): HttpHandler[] {
    // Records the request; returns the forced failure response if one is set.
    const record = (request: Request) => {
      const url = new URL(request.url);
      this.requests.push(`${request.method} ${url.pathname}${url.search}`);
      return this.failWith === null
        ? null
        : HttpResponse.json({ detail: "Crawler API is unreachable" }, { status: this.failWith });
    };
    const withCrawl = (
      request: Request,
      id: unknown,
      respond: (crawl: FakeCrawl) => Response | Promise<Response>,
    ) => {
      const failed = record(request);
      if (failed) return failed;
      const crawl = this.get(String(id));
      return crawl ? respond(crawl) : notFound(String(id));
    };

    return [
      http.get("*/api/crawls", ({ request }) => {
        const failed = record(request);
        if (failed) return failed;
        return HttpResponse.json([...this.crawls].reverse().map((c) => summaryOf(c.detail)));
      }),

      http.post("*/api/crawls", async ({ request }) => {
        const failed = record(request);
        if (failed) return failed;
        const body = (await request.json()) as CrawlRequest;
        this.started.push(body);
        if (this.holdStart) await this.holdStart;
        if (this.rejectStart) {
          return HttpResponse.json({ detail: this.rejectStart }, { status: 422 });
        }
        const crawl = makeCrawl({ url: body.url, status: "running", finished_at: null });
        this.add(crawl);
        return HttpResponse.json(summaryOf(crawl.detail), { status: 202 });
      }),

      http.get("*/api/crawls/:id", ({ request, params }) =>
        withCrawl(request, params.id, (crawl) => HttpResponse.json(crawl.detail)),
      ),

      http.delete("*/api/crawls/:id", ({ request, params }) =>
        withCrawl(request, params.id, (crawl) => {
          const id = crawl.detail.id;
          if (this.cancelLoses) {
            this.finish(id, this.cancelLoses);
            return HttpResponse.json(
              { detail: `crawl ${id} is already ${this.cancelLoses}` },
              { status: 409 },
            );
          }
          if (crawl.detail.status !== "running") {
            return HttpResponse.json({ detail: `crawl ${id} is already ${crawl.detail.status}` }, { status: 409 });
          }
          this.finish(id, "cancelled");
          return HttpResponse.json(crawl.detail);
        }),
      ),

      http.get("*/api/crawls/:id/status", ({ request, params }) =>
        withCrawl(request, params.id, (crawl) => HttpResponse.json(statusOf(crawl.detail))),
      ),

      http.get("*/api/crawls/:id/pages", ({ request, params }) =>
        withCrawl(request, params.id, (crawl) => {
          const { offset, limit } = paging(request);
          const items = crawl.pageUrls
            .slice(offset, offset + limit)
            .map((url) => ({ url, links: [`${url}#top`] }));
          return HttpResponse.json({ total: crawl.pageUrls.length, offset, limit, items });
        }),
      ),

      http.get("*/api/crawls/:id/links", ({ request, params }) =>
        withCrawl(request, params.id, (crawl) => {
          const { offset, limit } = paging(request);
          return HttpResponse.json({
            total: crawl.links.length,
            offset,
            limit,
            items: crawl.links.slice(offset, offset + limit),
          });
        }),
      ),
    ];
  }
}
