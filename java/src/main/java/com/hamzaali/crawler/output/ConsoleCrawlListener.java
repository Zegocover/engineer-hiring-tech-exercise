package com.hamzaali.crawler.output;

import java.io.PrintStream;
import java.net.URI;
import java.util.Comparator;
import java.util.Optional;

public final class ConsoleCrawlListener implements CrawlListener {

    private final PrintStream out;
    private final PrintStream log;

    public ConsoleCrawlListener(PrintStream out) {
        this(out, out);
    }

    public ConsoleCrawlListener(PrintStream out, PrintStream log) {
        this.out = Optional.ofNullable(out).orElseThrow(() -> new IllegalArgumentException("out must not be null"));
        this.log = Optional.ofNullable(log).orElseThrow(() -> new IllegalArgumentException("log must not be null"));
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

    @Override
    public void onSkipped(URI uri, String reason) {
        synchronized (log) {
            log.println("skipped " + uri + " (" + reason + ")");
        }
    }

    @Override
    public void onFailed(URI uri, String reason, String detail) {
        synchronized (log) {
            log.println("failed " + uri + " " + reason + " " + detail);
        }
    }
}
