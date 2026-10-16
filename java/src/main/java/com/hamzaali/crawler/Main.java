package com.hamzaali.crawler;

import com.hamzaali.crawler.cli.CrawlCommand;

public final class Main {

    private Main() {}

    public static void main(String[] args) {
        int exitCode = CrawlCommand.execute(args);
        System.exit(exitCode);
    }
}
