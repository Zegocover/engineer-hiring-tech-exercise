package com.hamzaali.crawler.parse;

import com.hamzaali.crawler.url.UrlNormalizer;
import java.net.URI;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;

public final class JsoupLinkExtractor implements LinkExtractor {

    private static final String LINK_SELECTOR = "a[href]";
    private static final String BASE_SELECTOR = "base[href]";

    @Override
    public Set<URI> extractLinks(URI page, String html) {
        Document document = Jsoup.parse(Optional.ofNullable(html).orElse(""));
        URI resolutionBase = documentBase(document, page).orElse(page);

        return document.select(LINK_SELECTOR).stream()
                .map(element -> element.attr("href"))
                .map(href -> UrlNormalizer.resolve(resolutionBase, href))
                .flatMap(Optional::stream)
                .collect(Collectors.toUnmodifiableSet());
    }

    private static Optional<URI> documentBase(Document document, URI page) {
        return document.select(BASE_SELECTOR).stream()
                .findFirst()
                .map(element -> element.attr("href"))
                .flatMap(href -> UrlNormalizer.resolve(page, href));
    }
}
