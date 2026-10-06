import type { CrawlError, CrawlResult, Reporter } from "./types"

export class ConsoleReporter implements Reporter {
  private crawledCount = 0

  onPageCrawled({ url, links }: CrawlResult): void {
    this.crawledCount++
    console.log(`\nVisited: ${url}`)

    if (links.length === 0) {
      console.log("  (no links on this domain)")
    } else {
      console.log(`  Links (${links.length}):`)
      for (const link of links) {
        console.log(`    -- ${link}`)
      }
    }
  }

  onPageError(url: string, error: unknown): void {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`\n[ERROR] ${url}`)
    console.error(`  ${message}`)
  }

  summarise(): void {
    console.log(
      `\n--- Crawl  is done! Hoorah! : ${this.crawledCount} page(s) visited ---`,
    )
  }
}

export class JsonReporter implements Reporter {
  private readonly pages: CrawlResult[] = []
  private readonly errors: Array<CrawlError> = []

  onPageCrawled(result: CrawlResult): void {
    this.pages.push(result)
  }

  onPageError(url: string, error: unknown): void {
    this.errors.push({
      url,
      error: error instanceof Error ? error.message : String(error),
    })
  }

  summarise(): void {
    console.log(
      JSON.stringify(
        {
          pagesVisited: this.pages.length,
          pages: this.pages,
          errors: this.errors,
        },
        null,
        2,
      ),
    )
  }
}
