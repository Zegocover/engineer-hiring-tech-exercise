package main

import (
	"context"
	"errors"
	"fmt"
	"io"
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

	if err := Run(ctx, slogger, os.Args[1:], os.Stdout); err != nil && !errors.Is(err, context.Canceled) {
		slogger.Error("Found an error while running", "error", err)
		os.Exit(1)
	}

	slogger.Info("Exited")
}

func Run(ctx context.Context, slogger *slog.Logger, args []string, writer io.Writer) error {
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

	res, err := crawler.Crawl(ctx, slogger, seedUrl)
	if err != nil {
		return fmt.Errorf("crawler seed url %s: %w", seedRawUrl, err)
	}

	for i := range res {
		if _, err := fmt.Fprintln(writer, res[i]); err != nil {
			return fmt.Errorf("writing URL: %w", err)
		}
	}

	return nil
}
