import { CheerioLinkExtractor } from "../link-extractor"

const BASE_URL = "https://example.com/page"
const extractor = new CheerioLinkExtractor()

describe("CheerioLinkExtractor", () => {
  it("extracts absolute href values from anchor tags", () => {
    const html = `<a href="https://example.com/about">About</a>`
    expect(extractor.extract(html, BASE_URL)).toEqual([
      "https://example.com/about",
    ])
  })

  it("strips fragments from discovered links", () => {
    const html = `<a href="/page#section">Link</a>`
    expect(extractor.extract(html, BASE_URL)).toEqual([
      "https://example.com/page",
    ])
  })

  it("deduplicates links that resolve to the same URL", () => {
    const html = `
      <a href="/page">Link 1</a>
      <a href="/page">Link 2</a>
      <a href="/page#fragment">Link 3</a>
    `
    expect(extractor.extract(html, BASE_URL)).toHaveLength(1)
  })

  it("ignores anchors without an href attribute", () => {
    const html = `<a name="section">Named anchor</a>`
    expect(extractor.extract(html, BASE_URL)).toHaveLength(0)
  })

  it("ignores non-HTTP links such as mailto", () => {
    const html = `<a href="mailto:user@example.com">Email</a>`
    expect(extractor.extract(html, BASE_URL)).toHaveLength(0)
  })

  it("ignores javascript: links", () => {
    const html = `<a href="javascript:void(0)">JS link</a>`
    expect(extractor.extract(html, BASE_URL)).toHaveLength(0)
  })

  it("returns an empty array when the page has no links", () => {
    const html = `<p>No links here</p>`
    expect(extractor.extract(html, BASE_URL)).toHaveLength(0)
  })

  it("returns links from different domains without filtering (domain filtering is the Crawler job)", () => {
    const html = `
      <a href="https://example.com/page1">Internal</a>
      <a href="https://other.com/page">External</a>
    `
    const links = extractor.extract(html, BASE_URL)
    expect(links).toContain("https://example.com/page1")
    expect(links).toContain("https://other.com/page")
    expect(links).toHaveLength(2)
  })
})
