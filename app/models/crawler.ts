import axios from 'axios'
import * as cheerio from 'cheerio'
import { CrawlerInterface } from '#types/crawler.interface'
import { getAbsoluteUrl } from '#helpers/utils'

export default class WebCrawler implements CrawlerInterface {
  baseUrl: URL

  pageAndItsLinks: Record<string, string[]>

  visitedLinks: Set<string>

  queue: string[]

  queueHead: number

  /**
   * The maximum number of concurrent workers to use.
   * @default 5
   */
  maxConcurrent: number

  /**
   * The maximum number of pages to crawl.
   * to avoid infinite loops.
   * @default 200
   */
  maxPagesToCrawl: number

  constructor(baseUrl: string, maxConcurrent = 5, maxPagesToCrawl = 200) {
    this.baseUrl = new URL(baseUrl)
    this.maxConcurrent = maxConcurrent
    this.maxPagesToCrawl = maxPagesToCrawl

    this.visitedLinks = new Set<string>()
    this.queue = [this.baseUrl.href]
    this.queueHead = 0
    this.pageAndItsLinks = {}
  }

  async loadUrl(url: string): Promise<string> {
    try {
      const response = await axios.get(url, {
        timeout: 10000,
        headers: { 'User-Agent': 'Node-Crawler/1.0' },
      })

      if (response.headers['content-type']?.includes('text/html') === false) {
        return ''
      }

      return response.data
    } catch (error: any) {
      console.warn(`Error loading: ${url}`, error.message)
      return ''
    }
  }

  extractLinks(htmlContent: string): string[] {
    const $ = cheerio.load(htmlContent)
    const foundUrls = new Set<string>()

    $('a[href]').each((_index, element) => {
      const href = $(element).attr('href')
      if (!href) return

      const link = getAbsoluteUrl(href, this.baseUrl.href)

      if (link) {
        foundUrls.add(link)
      }
    })

    return Array.from(foundUrls)
  }

  async crawlPage(url: string): Promise<void> {
    const htmlContent = await this.loadUrl(url)
    if (!htmlContent) {
      return
    }

    const extractedLinks = this.extractLinks(htmlContent)
    this.pageAndItsLinks[url] = extractedLinks

    for (const link of extractedLinks) {
      if (!this.visitedLinks.has(link)) {
        this.queue.push(link)
      }
    }

    /**
     * Log the extracted links for visibility purposes.
     */
    console.log({ url, extractedLinks })
  }

  async worker(): Promise<void> {
    while (this.queueHead < this.queue.length) {
      const currentUrl = this.queue[this.queueHead++]
      if (!currentUrl || this.visitedLinks.has(currentUrl)) continue

      this.visitedLinks.add(currentUrl)

      if (this.visitedLinks.size >= this.maxPagesToCrawl) {
        console.warn('limit reached')
        break
      }

      await this.crawlPage(currentUrl)

      if (this.queueHead > 1000) {
        this.queue = this.queue.slice(this.queueHead)
        this.queueHead = 0
      }
    }
  }

  async start(): Promise<void> {
    const workers = Array.from({ length: this.maxConcurrent }, () => this.worker())
    await Promise.allSettled(workers)

    console.log(this.visitedLinks.size, 'unique pages crawled ✅ ')
  }
}
