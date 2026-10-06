import { load } from "cheerio"
import type { LinkExtractor } from "./types"
import { normaliseUrl } from "./url-utils"

export class CheerioLinkExtractor implements LinkExtractor {
  extract(html: string, baseUrl: string): string[] {
    const $ = load(html)
    const seen = new Set<string>()
    const links: string[] = []

    $("a[href]").each((_index, element) => {
      const href = $(element).attr("href")
      if (!href) return

      const absolute = normaliseUrl(href, baseUrl)
      if (absolute && !seen.has(absolute)) {
        seen.add(absolute)
        links.push(absolute)
      }
    })

    return links
  }
}
