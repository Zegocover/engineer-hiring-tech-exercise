export interface CrawlResult {
  url: string
  /** Links found on this page that belong to the same subdomain. */
  links: string[]
}

export interface HttpResponse {
  html: string
  /** The URL after any redirects — used as the base for resolving relative links. */
  finalUrl: string
}

export interface HttpClient {
  /**
   * Fetches the HTML at `url`.
   * Returns `null` when the page should be skipped (e.g. non-HTML content, HTTP errors).
   * Throws on  network failures.
   */
  get(url: string): Promise<HttpResponse | null>
}

export interface LinkExtractor {
  extract(html: string, baseUrl: string): string[]
}

export interface Reporter {
  onPageCrawled(result: CrawlResult): void
  onPageError(url: string, error: unknown): void
  /** Called once after the crawl finishes to print a final summary. */
  summarise(): void
}

export interface CrawlerOptions {
  //Maximum number of concurrent in-flight HTTP requests. Default: 5.
  concurrency?: number
  // Stop after crawling this many pages.
  maxPages?: number
}

export interface CrawlError {
  url: string
  error: string
}
