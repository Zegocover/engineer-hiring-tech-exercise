package com.hamzaali.crawler.output;

import java.io.PrintStream;
import java.net.URI;
import java.util.Comparator;
import java.util.Optional;

public final class ConsoleCrawlListener implements CrawlListener {

    private final PrintStream out;

    public ConsoleCrawlListener(PrintStream out) {
        this.out = Optional.ofNullable(out).orElseThrow(() -> new IllegalArgumentException("out must not be null"));
    }

    @Override
    public void onPage(PageReport report) {
        synchronized (out) {
            out.println(report.page());
            report.links().stream()
                    .sorted(Comparator.comparing(URI::toString))
                    .forEach(link -> out.println("  " + link));
        }
    }
}
