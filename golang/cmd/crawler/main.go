package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"webcrawler/internal/crawler"
)

func main() {
	// Parse command line flags
	var (
		url       = flag.String("url", "", "Base URL to crawl (required)")
		workers   = flag.Int("workers", 10, "Number of concurrent workers")
		rateLimit = flag.Float64("rate", 5.0, "Requests per second")
		maxURLs   = flag.Int("max-urls", 0, "Maximum URLs to crawl (0 = unlimited)")
		useRedis  = flag.Bool("redis", false, "Enable Redis for distributed mode")
		redisAddr = flag.String("redis-addr", "localhost:6379", "Redis server address")
		userAgent = flag.String("user-agent", "GoCrawler/1.0", "User agent string")
	)

	flag.Parse()

	if *url == "" {
		fmt.Fprintln(os.Stderr, "Error: -url is required")
		flag.Usage()
		os.Exit(1)
	}

	// Configure crawler
	opts := crawler.DefaultOptions()
	opts.Workers = *workers
	opts.RateLimit = *rateLimit
	opts.MaxURLs = *maxURLs
	opts.UseRedis = *useRedis
	opts.RedisAddr = *redisAddr
	opts.UserAgent = *userAgent

	// Create crawler
	c, err := crawler.New(*url, opts)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating crawler: %v\n", err)
		os.Exit(1)
	}

	// Setup graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		fmt.Fprintln(os.Stderr, "\nShutting down...")
		cancel()
	}()

	// Print header
	fmt.Printf("Starting crawl of %s\n", *url)
	fmt.Printf("Workers: %d, Rate: %.1f req/s, Max URLs: %d\n", opts.Workers, opts.RateLimit, opts.MaxURLs)
	fmt.Println("---")

	// Run crawler
	results := c.Run(ctx)

	// Process results
	for result := range results {
		printResult(result)
	}

	// Print summary
	fmt.Println("---")
	fmt.Printf("Crawl complete. Total URLs crawled: %d\n", c.CrawledCount())
}

func printResult(result *crawler.Result) {
	fmt.Printf("URL: %s\n", result.URL)

	if result.Error != nil {
		fmt.Printf("Error: %v\n", result.Error)
	} else {
		if len(result.SameHost) > 0 || len(result.External) > 0 {
			fmt.Println("Found URLs:")
			for _, link := range result.SameHost {
				fmt.Printf("  - %s\n", link)
			}
			for _, link := range result.External {
				fmt.Printf("  - %s (external)\n", link)
			}
		}
	}

	fmt.Println("---")
}
