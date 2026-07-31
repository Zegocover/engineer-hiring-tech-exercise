import { isSameDomain, normaliseUrl } from "../url-utils"

describe("normaliseUrl", () => {
  it("returns an absolute URL unchanged (minus fragment)", () => {
    expect(normaliseUrl("https://example.com/path")).toBe(
      "https://example.com/path",
    )
  })

  it("resolves an absolute-path relative URL against the base", () => {
    expect(normaliseUrl("/about", "https://example.com/page")).toBe(
      "https://example.com/about",
    )
  })

  it("resolves a relative URL against the base", () => {
    expect(normaliseUrl("about", "https://example.com/dir/")).toBe(
      "https://example.com/dir/about",
    )
  })

  it("strips fragment identifiers", () => {
    expect(normaliseUrl("https://example.com/page#section")).toBe(
      "https://example.com/page",
    )
  })

  it("strips the fragment when resolving a relative URL", () => {
    expect(normaliseUrl("/page#anchor", "https://example.com/")).toBe(
      "https://example.com/page",
    )
  })

  it("keeps query strings", () => {
    expect(normaliseUrl("https://example.com/search?q=test")).toBe(
      "https://example.com/search?q=test",
    )
  })

  it("returns null for an invalid URL with no base", () => {
    expect(normaliseUrl("not a url")).toBeNull()
    expect(normaliseUrl("")).toBeNull()
  })

  it("returns null for non-http/https", () => {
    expect(normaliseUrl("mailto:user@example.com")).toBeNull()
    expect(normaliseUrl("javascript:void(0)")).toBeNull()
    expect(normaliseUrl("tel:+441234567890")).toBeNull()
    expect(normaliseUrl("ftp://example.com/")).toBeNull()
  })
})

describe("isSameDomain", () => {
  const origin = new URL("https://crawlme.monzo.com")

  it("returns true for the exact same hostname", () => {
    expect(isSameDomain("https://crawlme.monzo.com/page", origin)).toBe(true)
  })

  it("returns true regardless of the protocol", () => {
    expect(isSameDomain("http://crawlme.monzo.com/page", origin)).toBe(true)
  })

  it("returns false for a sibling subdomain", () => {
    expect(isSameDomain("https://community.monzo.com/page", origin)).toBe(false)
  })

  it("returns false for the parent domain", () => {
    expect(isSameDomain("https://monzo.com/page", origin)).toBe(false)
  })

  it("returns false for a completely different domain", () => {
    expect(isSameDomain("https://facebook.com/page", origin)).toBe(false)
  })

  it("returns false for an invalid URL", () => {
    expect(isSameDomain("not a url", origin)).toBe(false)
  })
})
