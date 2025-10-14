package navid.test.zego.service

import io.mola.galimatias.URL
import org.apache.commons.validator.routines.DomainValidator
import org.springframework.stereotype.Service

/**
 * Service for URL manipulation and validation.
 */
@Service
class UrlService {

    private val domainValidator = DomainValidator.getInstance()

    fun normalize(url: String, allowNonPublicHost: Boolean = false): String {
        val parsed = parseUrl(url)

        val host = parsed.host() ?: throw IllegalArgumentException("URL missing host")
        val path = parsed.path()?.trimEnd('/') ?: ""

        if (allowNonPublicHost.not() && isValidPublicUrl(url).not()) {
            throw IllegalArgumentException("URL is not a valid public url")
        }

        return buildString {
            append("${parsed.scheme()}://$host")
            if (path.isNotEmpty()) append(path)
        }
    }

    fun extractDomain(url: String): String = parseUrl(url).host().toHumanString()

    fun isSameDomain(url: String, baseDomain: String): Boolean = try {
        val host = extractDomain(url)
        host.equals(baseDomain, ignoreCase = true)
    } catch (_: Exception) {
        false
    }

    fun isValidPublicUrl(url: String): Boolean = try {
        val host = parseUrl(url).host()
        host != null && domainValidator.isValid(host.toHumanString())
    } catch (_: Exception) {
        false
    }

    private fun parseUrl(url: String): URL = URL.parse(url)
}