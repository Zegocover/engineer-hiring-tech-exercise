package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/rijude/single-domain-crawler/go/internal/crawler"
	"github.com/rijude/single-domain-crawler/go/internal/logging"
)

// main parses CLI options, runs the crawler, and writes the crawled URLs.
func main() {
	startURL := flag.String("startUrl", "", "URL where crawling starts")
	workers := flag.Int("workers", 1, "number of concurrent workers")
	logLevel := flag.String("log_level", "info", "log level: error, info, or debug")
	flag.Parse()
	logger := log.New(os.Stderr, "", log.LstdFlags)
	level, err := logging.ParseLogLevel(*logLevel)
	if err != nil {
		fail(logger, err.Error())
	}

	if strings.TrimSpace(*startURL) == "" {
		fail(logger, "startUrl is required")
	}
	if *workers < 1 {
		fail(logger, "workers must be at least 1")
	}

	appLogger := logging.NewLogger(logger, level)
	appLogger.Infof("starting scraping from %s with %d workers", *startURL, *workers)
	scrapeStarted := time.Now()
	urls, err := crawler.NewWithLogger(logger, level).Crawl(context.Background(), *startURL, *workers)
	if err != nil {
		fail(logger, err.Error())
	}
	appLogger.Infof(
		"finished scraping: %d URLs scraped with %d workers in %s",
		len(urls),
		*workers,
		time.Since(scrapeStarted),
	)

	appLogger.Infof("starting file creation: output.txt")
	output, err := os.Create("output.txt")
	if err != nil {
		fail(logger, fmt.Sprintf("create output.txt: %v", err))
	}
	defer output.Close()
	for _, crawledURL := range urls {
		if _, err := fmt.Fprintln(output, crawledURL); err != nil {
			fail(logger, fmt.Sprintf("write output.txt: %v", err))
		}
	}
	appLogger.Infof("finished file creation: output.txt")
}

// fail logs a fatal CLI error and exits with a failure status.
func fail(logger *log.Logger, message string) {
	logger.Printf("ERROR %s", message)
	os.Exit(1)
}
