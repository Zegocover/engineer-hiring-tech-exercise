export interface CrawlerInterface {
  baseUrl: URL
  pageAndItsLinks: Record<string, string[]>
  extractLinks(html: string): string[]
  loadUrl(url: string): Promise<string>
}
