const ignoredPrefixes = ['javascript:', 'mailto:', 'callto:', 'tel:']

/**
 * Constructs and returns an absolute URL by resolving it against a base URL.
 * If the URL contains certain ignored prefixes or an error occurs during processing, it returns `null`.
 *
 * @param {string} url - The relative or absolute URL to be resolved.
 * @param {string} baseUrl - The base URL to resolve the provided URL against.
 * @return {string | null} The absolute URL if successfully resolved, or `null` if the URL is invalid or ignored.
 */
export function getAbsoluteUrl(url: string, baseUrl: string): string | null {
  if (!url || ignoredPrefixes.some((pattern) => url.startsWith(pattern))) {
    return null
  }

  let base: URL
  try {
    base = new URL(baseUrl)
  } catch {
    return null
  }

  try {
    const resolvedUrl: URL = new URL(url, baseUrl)
    if (resolvedUrl.origin !== base.origin) {
      return null
    }

    resolvedUrl.hash = ''

    return resolvedUrl.href
  } catch (error: any) {
    console.warn(`Error parsing: ${url}`, error.message)
  }

  return null
}
