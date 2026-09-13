package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"os/signal"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
	"zego.com/engineer-hiring-tech-exercise/internal/crawler"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, os.Kill)
	defer stop()

	slogger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelDebug,
	}))
	slogger.Info("Starting crawler")

	if err := Run(ctx, slogger, os.Args[1:]); err != nil && !errors.Is(err, context.Canceled) {
		slogger.Error("Found an error while running", "error", err)
		os.Exit(1)
	}

	slogger.Info("Exited")
}

func Run(ctx context.Context, slogger *slog.Logger, args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("not enough arguments")
	}

	seedRawUrl := args[0]

	seedUrl, err := url.Parse(seedRawUrl)
	if err != nil {
		return fmt.Errorf("parsing seed url %s: %w", seedRawUrl, err)
	}

	client := client.NewClient()
	crawler := crawler.NewCrawler(client)

	report, err := crawler.Crawl(ctx, slogger, seedUrl)
	if err != nil {
		return fmt.Errorf("crawler seed url %s: %w", seedRawUrl, err)
	}

	for i := range report.External {
		slogger.Debug("External Links", "url", report.External[i].String())
	}

	for i := range report.Internal {
		slogger.Debug("Internal links", "url", report.Internal[i].String())
	}

	return nil
}
