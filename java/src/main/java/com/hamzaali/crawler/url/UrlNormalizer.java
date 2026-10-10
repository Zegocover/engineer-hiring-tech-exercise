package com.hamzaali.crawler.url;

import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;
import java.util.regex.Pattern;

/**
 * The single place where URLs are canonicalised, so that every spelling of the same page maps to one {@link URI}
 * and the page is fetched only once.
 *
 * <p>Path case, trailing slashes and query strings are preserved because servers are free to treat them as
 * different resources.
 */
public final class UrlNormalizer {

    private static final Set<String> CRAWLABLE_SCHEMES = Set.of("http", "https");
    private static final String CHARACTERS_ILLEGAL_IN_URI = "\"<>\\^`{|}";
    private static final Pattern TABS_AND_NEWLINES = Pattern.compile("[\t\n\r]");
    private static final HexFormat UPPERCASE_HEX = HexFormat.of().withUpperCase();

    private UrlNormalizer() {}

    public static Optional<URI> normalize(String url) {
        return Optional.ofNullable(url)
                .map(UrlNormalizer::removeWhitespace)
                .flatMap(UrlNormalizer::parseUri)
                .flatMap(UrlNormalizer::canonicalize);
    }

    public static Optional<URI> resolve(URI page, String href) {
        return canonicalize(page)
                .flatMap(canonicalPage -> Optional.ofNullable(href)
                        .map(UrlNormalizer::removeWhitespace)
                        .filter(Predicate.not(UrlNormalizer::isSamePageReference))
                        .flatMap(UrlNormalizer::parseUri)
                        .map(reference -> resolveReference(canonicalPage, reference))
                        .flatMap(UrlNormalizer::canonicalize));
    }

    private static boolean isSamePageReference(String href) {
        return href.isEmpty() || href.startsWith("#");
    }

    /** Malformed links are common in real HTML, so they are dropped rather than failing the whole page. */
    private static Optional<URI> parseUri(String value) {
        return Optional.of(value).filter(Predicate.not(String::isEmpty)).flatMap(UrlNormalizer::createUri);
    }

    private static Optional<URI> createUri(String value) {
        try {
            return Optional.of(new URI(percentEncodeIllegalCharacters(value)));
        } catch (URISyntaxException malformed) {
            return Optional.empty();
        }
    }

    private static URI resolveReference(URI page, URI reference) {
        return isQueryOnly(reference) ? resolveQueryReference(page, reference) : page.resolve(reference);
    }

    /** URI.resolve follows RFC 2396, which drops the page name for "?query" links; browsers keep it. */
    private static URI resolveQueryReference(URI page, URI reference) {
        return URI.create(
                page.getScheme() + "://" + page.getRawAuthority() + page.getRawPath() + "?" + reference.getRawQuery());
    }

    private static boolean isQueryOnly(URI reference) {
        return !reference.isAbsolute()
                && Optional.ofNullable(reference.getRawAuthority()).isEmpty()
                && reference.getRawPath().isEmpty()
                && Optional.ofNullable(reference.getRawQuery()).isPresent();
    }

    private static Optional<URI> canonicalize(URI uri) {
        return Optional.ofNullable(uri)
                .filter(Predicate.not(URI::isOpaque))
                .map(URI::normalize)
                .flatMap(UrlNormalizer::canonicalizeHierarchicalUri);
    }

    private static Optional<URI> canonicalizeHierarchicalUri(URI uri) {
        return crawlableScheme(uri)
                .flatMap(scheme -> hostAndPort(uri).map(authority -> buildCanonicalUri(uri, scheme, authority)));
    }

    private static Optional<String> crawlableScheme(URI uri) {
        return Optional.ofNullable(uri.getScheme())
                .map(scheme -> scheme.toLowerCase(Locale.ROOT))
                .filter(CRAWLABLE_SCHEMES::contains);
    }

    /**
     * java.net.URI leaves getHost() empty for names such as {@code sub.127.0.0.1}, because the last labels look like
     * a broken IPv4 address. Browsers still treat that as a hostname, so we fall back to the raw authority.
     */
    private static Optional<HostAndPort> hostAndPort(URI uri) {
        return Optional.ofNullable(uri.getHost())
                .map(host -> new HostAndPort(host.toLowerCase(Locale.ROOT), uri.getPort()))
                .or(() -> hostAndPortFromAuthority(uri.getRawAuthority()));
    }

    private static Optional<HostAndPort> hostAndPortFromAuthority(String authority) {
        return Optional.ofNullable(authority)
                .map(UrlNormalizer::stripUserInfo)
                .flatMap(UrlNormalizer::splitHostAndPort)
                .filter(value -> !value.host().isEmpty());
    }

    private static String stripUserInfo(String authority) {
        int userInfoEnd = authority.lastIndexOf('@');
        return userInfoEnd >= 0 ? authority.substring(userInfoEnd + 1) : authority;
    }

    private static Optional<HostAndPort> splitHostAndPort(String hostPort) {
        if (hostPort.startsWith("[")) {
            int close = hostPort.indexOf(']');
            if (close < 0) {
                return Optional.empty();
            }
            String host = hostPort.substring(0, close + 1).toLowerCase(Locale.ROOT);
            return Optional.of(new HostAndPort(host, portAfter(hostPort, close + 1)));
        }
        int colon = hostPort.lastIndexOf(':');
        if (colon < 0) {
            return Optional.of(new HostAndPort(hostPort.toLowerCase(Locale.ROOT), -1));
        }
        return Optional.of(
                new HostAndPort(hostPort.substring(0, colon).toLowerCase(Locale.ROOT), portAfter(hostPort, colon)));
    }

    private static int portAfter(String hostPort, int separatorIndex) {
        if (separatorIndex + 1 >= hostPort.length() || hostPort.charAt(separatorIndex) != ':') {
            return -1;
        }
        try {
            return Integer.parseInt(hostPort.substring(separatorIndex + 1));
        } catch (NumberFormatException malformedPort) {
            return -1;
        }
    }

    private static URI buildCanonicalUri(URI uri, String scheme, HostAndPort authority) {
        // Built from raw components because URI's multi-argument constructors decode and re-encode,
        // which would turn escapes such as %2F into real path separators.
        String canonical = scheme
                + "://"
                + canonicalAuthority(scheme, authority)
                + canonicalPath(uri.getRawPath())
                + querySuffix(uri);
        return URI.create(canonical);
    }

    /** User info is dropped so that credentials embedded in links are never printed or sent to a server. */
    private static String canonicalAuthority(String scheme, HostAndPort authority) {
        return isDefaultPort(scheme, authority.port()) ? authority.host() : authority.host() + ":" + authority.port();
    }

    private static boolean isDefaultPort(String scheme, int port) {
        int defaultPort = scheme.equals("https") ? 443 : 80;
        return port == -1 || port == defaultPort;
    }

    private static String canonicalPath(String rawPath) {
        return Optional.ofNullable(rawPath)
                .filter(Predicate.not(String::isEmpty))
                .map(UrlNormalizer::removeDotSegmentsAboveRoot)
                .orElse("/");
    }

    /** URI.normalize keeps ".." segments that climb above the root, whereas browsers discard them. */
    private static String removeDotSegmentsAboveRoot(String path) {
        String result = path;
        while (result.startsWith("/../")) {
            result = result.substring("/..".length());
        }
        return result.equals("/..") ? "/" : result;
    }

    private static String querySuffix(URI uri) {
        return Optional.ofNullable(uri.getRawQuery()).map(query -> "?" + query).orElse("");
    }

    /** Browsers ignore whitespace around a link and any tabs or newlines inside it. */
    private static String removeWhitespace(String value) {
        return TABS_AND_NEWLINES.matcher(value.strip()).replaceAll("");
    }

    /** Real-world links often contain spaces or non-ASCII characters that browsers encode but java.net.URI rejects. */
    private static String percentEncodeIllegalCharacters(String value) {
        StringBuilder encoded = new StringBuilder(value.length());
        int index = 0;
        while (index < value.length()) {
            int codePoint = value.codePointAt(index);
            if (codePoint == '%' && !isPercentEscape(value, index)) {
                encoded.append("%25");
            } else if (isLegalUriCharacter(codePoint)) {
                encoded.appendCodePoint(codePoint);
            } else {
                appendPercentEncoded(encoded, codePoint);
            }
            index += Character.charCount(codePoint);
        }
        return encoded.toString();
    }

    private static boolean isPercentEscape(String value, int index) {
        return index + 2 < value.length()
                && HexFormat.isHexDigit(value.charAt(index + 1))
                && HexFormat.isHexDigit(value.charAt(index + 2));
    }

    private static boolean isLegalUriCharacter(int codePoint) {
        return codePoint > ' ' && codePoint < 0x7F && CHARACTERS_ILLEGAL_IN_URI.indexOf(codePoint) < 0;
    }

    private static void appendPercentEncoded(StringBuilder target, int codePoint) {
        for (byte utf8Byte : Character.toString(codePoint).getBytes(StandardCharsets.UTF_8)) {
            target.append('%').append(UPPERCASE_HEX.toHexDigits(utf8Byte));
        }
    }

    private record HostAndPort(String host, int port) {}
}
