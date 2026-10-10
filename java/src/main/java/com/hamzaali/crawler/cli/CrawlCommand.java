package com.hamzaali.crawler.cli;

import java.time.Clock;
import java.time.Duration;
import java.util.concurrent.Callable;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

@Command(
        name = "crawler",
        mixinStandardHelpOptions = true,
        description = "Crawl a single host and print each page URL with the links found on it.")
public final class CrawlCommand implements Callable<Integer> {

    static final String DEFAULT_USER_AGENT = "ZegoCrawler/0.1";

    @Parameters(index = "0", paramLabel = "URL", description = "Starting URL. https:// is added if no scheme is given.")
    private String url;

    @Option(
            names = {"-c", "--concurrency"},
            description = "Maximum parallel fetches. Default: ${DEFAULT-VALUE}")
    private int concurrency = 10;

    @Option(
            names = {"-t", "--timeout"},
            description = "Request timeout in seconds. Default: ${DEFAULT-VALUE}")
    private int timeoutSeconds = 10;

    @Option(
            names = {"--max-depth"},
            description = "Maximum link depth from the start URL. Default: ${DEFAULT-VALUE}")
    private int maxDepth = 64;

    @Option(
            names = {"--max-redirects"},
            description = "Maximum redirects followed per request. Default: ${DEFAULT-VALUE}")
    private int maxRedirects = 5;

    @Option(
            names = {"--max-response-bytes"},
            description = "Maximum HTML body size in bytes. Default: ${DEFAULT-VALUE}")
    private int maxResponseBytes = 2_000_000;

    @Option(
            names = {"--user-agent"},
            description = "User-Agent header sent with each request.")
    private String userAgent = DEFAULT_USER_AGENT;

    private final CrawlRunner runner;

    public CrawlCommand() {
        this(new CrawlRunner(System.out, System.err, Clock.systemUTC()));
    }

    CrawlCommand(CrawlRunner runner) {
        this.runner = runner;
    }

    @Override
    public Integer call() throws Exception {
        runner.run(settings());
        return 0;
    }

    CrawlSettings settings() {
        return new CrawlSettings(
                CrawlSettings.parseSeed(url),
                concurrency,
                Duration.ofSeconds(timeoutSeconds),
                maxDepth,
                maxRedirects,
                maxResponseBytes,
                userAgent);
    }

    public static int execute(String... args) {
        return new CommandLine(new CrawlCommand()).execute(args);
    }
}
