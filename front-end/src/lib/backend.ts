import "server-only";

/** Where the crawler API runs when CRAWLER_API_URL isn't set. */
export const DEFAULT_CRAWLER_API_URL = "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 10_000;

export function crawlerApiUrl(): string {
  return (process.env.CRAWLER_API_URL || DEFAULT_CRAWLER_API_URL).replace(/\/+$/, "");
}

/**
 * Sends ``request`` on to the crawler API at ``path`` and returns its answer unchanged.
 *
 * The query string and JSON body are copied across. If the crawler API can't be
 * reached or doesn't answer in time, responds 502 instead. The crawler API's
 * address is only logged, never sent back to the browser.
 */
export async function forward(
  request: Request,
  path: string,
  { timeoutMs = DEFAULT_TIMEOUT_MS }: { timeoutMs?: number } = {},
): Promise<Response> {
  const base = crawlerApiUrl();
  const url = `${base}${path}${new URL(request.url).search}`;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.text() : "";

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: request.method,
      headers: body ? { "content-type": "application/json" } : undefined,
      body: body || undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    console.error(`crawler API request failed: ${request.method} ${url}:`, error);
    return Response.json({ detail: "Crawler API is unreachable" }, { status: 502 });
  }

  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

/** Escapes a crawl id taken from the URL before it goes into a crawler API path. */
export function crawlPath(id: string, suffix = ""): string {
  return `/crawls/${encodeURIComponent(id)}${suffix}`;
}
