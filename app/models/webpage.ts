import axios from 'axios'
import * as cheerio from 'cheerio'
import { WebpageInterface } from '../interfaces/webpage_interface.js'

export default class Webpage implements WebpageInterface {
  url: URL

  links: string[] = []

  htmlContent: string = ''

  constructor(baseURL: string) {
    this.url = new URL(baseURL)
  }

  async getLinks(): Promise<string[]> {
    this.links = await this.crawlLinks()

    return this.links
  }

  async load(): Promise<void> {
    const response = await axios.get(this.url.href, {
      timeout: 10000,
      headers: { 'User-Agent': 'Node-Crawler/1.0' },
    })

    if (response.headers['content-type']?.includes('text/html') === false) {
      return
    }

    this.htmlContent = response.data
  }

  private async crawlLinks(): Promise<string[]> {
    const $ = cheerio.load(this.htmlContent)
    const foundUrls = new Set<string>()

    $('a[href]').each((_index, element) => {
      const href = $(element).attr('href')
      if (!href) return

      const absoluteUrl = this.getAbsoluteUrl(href)

      if (absoluteUrl) {
        foundUrls.add(absoluteUrl)
      }
    })

    return Array.from(foundUrls)
  }

  private getAbsoluteUrl(link: string): string | null {
    try {
      const resolvedUrl: URL = new URL(link, this.url.href)

      if (resolvedUrl.hostname === this.url.hostname) {
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
