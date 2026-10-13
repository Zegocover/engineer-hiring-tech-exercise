package com.hamzaali.crawler.cli;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.URI;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import picocli.CommandLine;

class CrawlCommandTest {

    @Test
    void shouldParseUrlAndOverrides() {
        CrawlCommand command = new CrawlCommand();

        new CommandLine(command)
                .parseArgs(
                        "example.com",
                        "-c",
                        "4",
                        "-t",
                        "15",
                        "--max-depth",
                        "2",
                        "--max-pages",
                        "7",
                        "--max-redirects",
                        "1",
                        "--max-response-bytes",
                        "5000",
                        "--user-agent",
                        "TestAgent/1.0",
                        "--no-robots");

        assertThat(command.settings())
                .isEqualTo(new CrawlSettings(
                        URI.create("https://example.com/"),
                        4,
                        Duration.ofSeconds(15),
                        2,
                        7,
                        1,
                        5000,
                        "TestAgent/1.0",
                        false));
    }

    @Test
    void shouldUseDefaultsWhenOnlyUrlIsGiven() {
        CrawlCommand command = new CrawlCommand();

        new CommandLine(command).parseArgs("https://example.com/start");

        assertThat(command.settings())
                .isEqualTo(new CrawlSettings(
                        URI.create("https://example.com/start"),
                        10,
                        Duration.ofSeconds(10),
                        64,
                        0,
                        5,
                        2_000_000,
                        CrawlCommand.DEFAULT_USER_AGENT,
                        true));
    }

    @Test
    void shouldReturnUsageWhenHelpIsRequested() {
        StringWriter output = new StringWriter();
        CommandLine commandLine = new CommandLine(new CrawlCommand());
        commandLine.setOut(new PrintWriter(output));

        int exitCode = commandLine.execute("--help");

        assertThat(exitCode).isZero();
        assertThat(output.toString()).contains("Usage: crawler");
    }

    @Test
    void shouldFailWhenUrlIsMissing() {
        int exitCode = new CommandLine(new CrawlCommand()).execute();

        assertThat(exitCode).isNotZero();
    }
}
