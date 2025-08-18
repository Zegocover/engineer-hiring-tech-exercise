import axios from 'axios'
import * as cheerio from 'cheerio'

export default class WebCrawler {
  baseUrl: URL

  pageAndItsLinks: Record<string, string[]> = {}

  visitedLinks: Set<string> = new Set<string>()

  queue: string[] = []

  constructor(baseUrl: string) {
    this.baseUrl = new URL(baseUrl)
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

  private async crawlPageRecursively(baseUrl: string): Promise<void> {
    if (this.visitedLinks.has(baseUrl)) {
      return
    }

    this.visitedLinks.add(baseUrl)

    const htmlContent = await this.loadUrl(baseUrl)
    if (!htmlContent) {
      return
    }

    const $ = cheerio.load(htmlContent)
    const foundUrls = new Set<string>()

    $('a[href]').each((_index, element) => {
      const href = $(element).attr('href')
      if (!href) return

      const absoluteUrl = this.getAbsoluteUrl(href)

      if (absoluteUrl) {
        foundUrls.add(absoluteUrl)

        if (!this.visitedLinks.has(absoluteUrl)) {
          this.queue.push(absoluteUrl)
        }
      }
    })

    console.log({ page: baseUrl, links: Array.from(foundUrls) })

    this.pageAndItsLinks[baseUrl] = Array.from(foundUrls)
  }

  public async start(): Promise<void> {
    this.queue.push(this.baseUrl.href)

    while (this.queue.length > 0) {
      const currentUrl = this.queue.shift()
      if (!currentUrl) continue

      await this.crawlPageRecursively(currentUrl)

      if (this.visitedLinks.size >= 200) {
        console.warn('limit reached')

        break
      }
    }

    console.log(`Total unique pages crawled: ${this.visitedLinks.size}`)
  }

  private getAbsoluteUrl(link: string): string | null {
    try {
      const resolvedUrl: URL = new URL(link, this.baseUrl.href)

      if (resolvedUrl.hostname === this.baseUrl.hostname) {
        resolvedUrl.hash = ''
        return resolvedUrl.href
      }
    } catch (error: any) {
      console.warn(`Error parsing: ${link}`, error.message)
      return null
    }

    return null
  }
}
