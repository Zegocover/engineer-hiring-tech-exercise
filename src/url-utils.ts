/**
 * Returns `null` for invalid URLs or non-HTTP(S) schemes (e.g. mailto:, tel:, javascript:).
 */
export function normaliseUrl(url: string, base?: string): string | null {
  try {
    const parsed = new URL(url, base)
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return null
    }
    // Two pages that differ only by fragment are the same resource.
    parsed.hash = ""
    return parsed.href
  } catch {
    return null
  }
}

export function isSameDomain(url: string, origin: URL): boolean {
  try {
    return new URL(url).hostname === origin.hostname
  } catch {
    return false
  }
}
