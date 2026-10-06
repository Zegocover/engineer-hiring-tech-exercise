import { Crawler } from "../crawler"
import type {
  CrawlResult,
  HttpClient,
  HttpResponse,
  LinkExtractor,
  Reporter,
} from "../types"

// ─── Test helpers ─────────────────────────────────────────────────────────────

const HTML = "<html><body>test</body></html>"

function makeClient(
  responses: Record<string, HttpResponse | null>,
): HttpClient {
  return {
    get: jest.fn(async (url: string) => responses[url] ?? null),
  }
}

/** Extractor backed by a map of finalUrl → links[]. */
function makeExtractor(links: Record<string, string[]>): LinkExtractor {
  return {
    extract: jest.fn((_html: string, baseUrl: string) => links[baseUrl] ?? []),
  }
}

function makeReporter(): Reporter & {
  crawled: CrawlResult[]
  errors: Array<{ url: string; error: unknown }>
} {
  const crawled: CrawlResult[] = []
  const errors: Array<{ url: string; error: unknown }> = []
  return {
    crawled,
    errors,
    onPageCrawled: jest.fn((result) => crawled.push(result)),
    onPageError: jest.fn((url, error) => errors.push({ url, error })),
    summarise: jest.fn(),
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Crawler", () => {
  it("crawls a single page with no links", async () => {
    const url = "https://example.com/"
    const reporter = makeReporter()
    const c = new Crawler(
      makeClient({ [url]: { html: HTML, finalUrl: url } }),
      makeExtractor({ [url]: [] }),
      reporter,
    )

    await c.crawl(url)

    expect(reporter.crawled).toHaveLength(1)
    expect(reporter.crawled[0]).toEqual({ url, links: [] })
    expect(reporter.errors).toHaveLength(0)
  })

  it("follows links on the same domain", async () => {
    const home = "https://example.com/"
    const about = "https://example.com/about"
    const reporter = makeReporter()

    const c = new Crawler(
      makeClient({
        [home]: { html: HTML, finalUrl: home },
        [about]: { html: HTML, finalUrl: about },
      }),
      makeExtractor({ [home]: [about], [about]: [] }),
      reporter,
    )

    await c.crawl(home)

    expect(reporter.crawled).toHaveLength(2)
    const urls = reporter.crawled.map((r) => r.url)
    expect(urls).toContain(home)
    expect(urls).toContain(about)
  })

  it("does not follow links to a different domain", async () => {
    const home = "https://example.com/"
    const external = "https://external.com/page"
    const reporter = makeReporter()
    const client = makeClient({ [home]: { html: HTML, finalUrl: home } })

    const c = new Crawler(
      client,
      makeExtractor({ [home]: [external] }),
      reporter,
    )

    await c.crawl(home)

    expect(reporter.crawled).toHaveLength(1)
    expect(client.get).toHaveBeenCalledTimes(1)
  })

  it("does not follow links to a sibling subdomain or parent domain", async () => {
    const home = "https://crawlme.monzo.com/"
    const reporter = makeReporter()
    const client = makeClient({ [home]: { html: HTML, finalUrl: home } })

    const c = new Crawler(
      client,
      makeExtractor({
        [home]: [
          "https://monzo.com/page",
          "https://community.monzo.com/page",
          "https://facebook.com/page",
        ],
      }),
      reporter,
    )

    await c.crawl(home)

    expect(reporter.crawled).toHaveLength(1)
    expect(client.get).toHaveBeenCalledTimes(1)
  })

  it("does not revisit pages already in the visited set (handles cycles)", async () => {
    const pageA = "https://example.com/a"
    const pageB = "https://example.com/b"
    const reporter = makeReporter()
    const client = makeClient({
      [pageA]: { html: HTML, finalUrl: pageA },
      [pageB]: { html: HTML, finalUrl: pageB },
    })

    const c = new Crawler(
      client,
      // A → B → A forms a cycle
      makeExtractor({ [pageA]: [pageB], [pageB]: [pageA] }),
      reporter,
    )

    await c.crawl(pageA)

    expect(reporter.crawled).toHaveLength(2)
    expect(client.get).toHaveBeenCalledTimes(2)
  })

  it("treats a null HTTP response as a page with no links (non-HTML / HTTP error)", async () => {
    const home = "https://example.com/"
    const image = "https://example.com/image.png"
    const reporter = makeReporter()

    const c = new Crawler(
      makeClient({
        [home]: { html: HTML, finalUrl: home },
        [image]: null,
      }),
      makeExtractor({ [home]: [image] }),
      reporter,
    )

    await c.crawl(home)

    expect(reporter.errors).toHaveLength(0)
    expect(reporter.crawled).toHaveLength(2)
    const imageResult = reporter.crawled.find((r) => r.url === image)
    expect(imageResult?.links).toEqual([])
  })

  it("reports network failures and continues crawling other pages", async () => {
    const home = "https://example.com/"
    const page2 = "https://example.com/page2"
    const page3 = "https://example.com/page3"
    const networkError = new Error("ECONNREFUSED")
    const reporter = makeReporter()

    const client: HttpClient = {
      get: jest
        .fn()
        .mockResolvedValueOnce({ html: HTML, finalUrl: home })
        // page2 and page3 are in the same batch; page2 fails, page3 succeeds
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce({ html: HTML, finalUrl: page3 }),
    }

    const c = new Crawler(
      client,
      makeExtractor({ [home]: [page2, page3], [page3]: [] }),
      reporter,
      { concurrency: 5 },
    )

    await c.crawl(home)

    expect(reporter.errors).toHaveLength(1)
    expect(reporter.errors[0].url).toBe(page2)
    expect(reporter.crawled).toHaveLength(2) // home + page3
  })

  it("stops after maxPages pages have been crawled", async () => {
    const pages = [
      "https://example.com/",
      "https://example.com/1",
      "https://example.com/2",
    ]
    const reporter = makeReporter()

    const responses = Object.fromEntries(
      pages.map((p) => [p, { html: HTML, finalUrl: p }]),
    )
    // Each page links to the next
    const links: Record<string, string[]> = {
      [pages[0]]: [pages[1]],
      [pages[1]]: [pages[2]],
      [pages[2]]: [],
    }

    const c = new Crawler(
      makeClient(responses),
      makeExtractor(links),
      reporter,
      {
        maxPages: 2,
      },
    )

    await c.crawl(pages[0])

    expect(reporter.crawled).toHaveLength(2)
  })

  it("throws a RangeError when constructed with concurrency < 1", () => {
    expect(
      () =>
        new Crawler({} as HttpClient, {} as LinkExtractor, {} as Reporter, {
          concurrency: 0,
        }),
    ).toThrow(RangeError)
  })

  it("throws for an invalid start URL", async () => {
    const c = new Crawler({} as HttpClient, {} as LinkExtractor, {} as Reporter)
    await expect(c.crawl("not-a-url")).rejects.toThrow()
  })
})
