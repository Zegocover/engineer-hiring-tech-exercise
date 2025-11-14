package crawler

import java.net.URI

interface UrlNormalizer {
    fun normalize(base: URI, link: String): URI?
}

class DefaultUrlNormalizer : UrlNormalizer {

    override fun normalize(base: URI, link: String): URI? {
        if (link.isBlank()) return null

        return try {
            val resolved = base.resolve(link).normalize()
            // Drop fragments and query parameters for dedupe
            URI(
                resolved.scheme,
                resolved.authority,
                resolved.path,
                null,
                null
            )
        } catch (e: Exception) {
            null
        }
    }
}