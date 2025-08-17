export interface WebpageInterface {
  url: URL
  links: string[]
  htmlContent: string
  getLinks(): Promise<string[]>
  load(): Promise<void>
}
