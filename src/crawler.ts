import type {
  CrawlResult,
  CrawlerOptions,
  HttpClient,
  LinkExtractor,
  Reporter,
} from "./types"
import { isSameDomain, normaliseUrl } from "./url-utils"

export class Crawler {
  private readonly concurrency: number
  private readonly maxPages: number

  constructor(
    private readonly client: HttpClient,
    private readonly extractor: LinkExtractor,
    private readonly reporter: Reporter,
    //I think having a sensible default makes sense
    { concurrency = 5, maxPages = 10000 }: CrawlerOptions = {},
  ) {
    if (concurrency < 1) throw new RangeError("concurrency must be at least 1")
    this.concurrency = concurrency
    this.maxPages = maxPages
  }

  async crawl(startUrl: string): Promise<void> {
    // new URL() throws a TypeError for an invalid URL — intentional: fail fast.
    const origin = new URL(startUrl)
    const visited = new Set<string>()
    const queue: string[] = []
    let crawledCount = 0

    const discover = (url: string): void => {
      const normalised = normaliseUrl(url)
      if (
        normalised &&
        isSameDomain(normalised, origin) &&
        !visited.has(normalised)
      ) {
        visited.add(normalised)
        queue.push(normalised)
      }
    }

    discover(startUrl)

    while (queue.length > 0 && crawledCount < this.maxPages) {
      const remaining = this.maxPages - crawledCount
      const batch = queue.splice(0, Math.min(this.concurrency, remaining))

      // Promise.allSettled ensures 1 failure doesnt break the whole batch
      const results = await Promise.allSettled(
        batch.map((url) => this.fetchPage(url, origin)),
      )

      crawledCount += batch.length

      results.forEach((result, index) => {
        const url = batch[index]
        if (result.status === "rejected") {
          this.reporter.onPageError(url, result.reason)
        } else {
          this.reporter.onPageCrawled(result.value)
          result.value.links.forEach(discover)
        }
      })
    }
  }

  private async fetchPage(url: string, origin: URL): Promise<CrawlResult> {
    const response = await this.client.get(url)

    if (!response) {
      // Non-HTML resource or HTTP error — report as a visited page with no links.
      return { url, links: [] }
    }

    const allLinks = this.extractor.extract(response.html, response.finalUrl)

    const links = allLinks.filter((link) => isSameDomain(link, origin))

    return { url, links }
  }
}
