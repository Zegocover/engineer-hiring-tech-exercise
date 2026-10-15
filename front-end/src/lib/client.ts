// Browser-side calls to the dashboard's own /api routes, typed with the crawler API's models.
import type {
  CrawlDetail,
  CrawlRequest,
  CrawlStatus,
  CrawlSummary,
  ErrorBody,
  JobStatus,
  LinkList,
  PageList,
  ValidationError,
} from "./api/types";

/** Page size for the pages and links tabs. */
export const PAGE_SIZE = 50;

/** A response from the dashboard's API that wasn't 2xx. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string | ValidationError[],
  ) {
    super(typeof detail === "string" ? detail : detail.map((e) => e.msg).join("; "));
    this.name = "ApiError";
  }

  /** Validation errors from a 422, or an empty list for any other error. */
  get validationErrors(): ValidationError[] {
    return Array.isArray(this.detail) ? this.detail : [];
  }
}

export function isRunning(status: JobStatus | undefined): boolean {
  return status === "running";
}

function apiUrl(path: string): string {
  // Absolute URL: relative fetch URLs don't resolve outside a browser (e.g. jsdom tests).
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  return new URL(path, origin).toString();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: init?.body ? { "content-type": "application/json" } : undefined,
  });
  if (!response.ok) {
    let detail: ErrorBody["detail"] = response.statusText || `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as Partial<ErrorBody>;
      if (body.detail !== undefined) detail = body.detail;
    } catch {
      // Not JSON (e.g. Next.js's HTML 404 page): keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

const crawl = (id: string, suffix = "") => `/api/crawls/${encodeURIComponent(id)}${suffix}`;
const range = (offset: number, limit: number) => `?offset=${offset}&limit=${limit}`;

export const api = {
  listCrawls: () => request<CrawlSummary[]>("/api/crawls"),
  startCrawl: (body: CrawlRequest) =>
    request<CrawlSummary>("/api/crawls", { method: "POST", body: JSON.stringify(body) }),
  getCrawl: (id: string) => request<CrawlDetail>(crawl(id)),
  getStatus: (id: string) => request<CrawlStatus>(crawl(id, "/status")),
  getPages: (id: string, offset: number, limit = PAGE_SIZE) =>
    request<PageList>(crawl(id, `/pages${range(offset, limit)}`)),
  getLinks: (id: string, offset: number, limit = PAGE_SIZE) =>
    request<LinkList>(crawl(id, `/links${range(offset, limit)}`)),
  cancelCrawl: (id: string) => request<CrawlDetail>(crawl(id), { method: "DELETE" }),
};
