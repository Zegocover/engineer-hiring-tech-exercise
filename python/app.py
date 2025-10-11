#!/usr/bin/env python
"""
Main application entry point for the web crawler. This script handles command-line arguments,
"""
import argparse
import sys

from core.crawler_service import CrawlerService
from configuration.config import CrawlerConfig
from data.exceptions import CrawlerServiceError

def run_crawler(config: CrawlerConfig):
    try:
        # Step 1: Create the crawler service with our configuration
        crawler = CrawlerService(config)
        
        # Step 2: Start the crawling process and get summary results
        # This will:
        # - Visit the starting URL
        # - Extract links from each page
        # - Follow links to same-domain pages
        # - Continue until no new links found or stopped by user
        summary = crawler.run()
        
        # Step 3: Display detailed results to the user
        print(f"\n{'='*50}")
        print(f"CRAWL SUMMARY")
        print(f"{'='*50}")
        
        # Show basic statistics about the crawling session
        print(f"Base URL: {summary.base_url}")                    # Where we started
        print(f"Total pages crawled: {summary.total_pages}")      # How many pages visited
        print(f"Successful pages: {summary.successful_pages}")    # How many loaded successfully
        print(f"Failed pages: {summary.failed_pages}")           # How many had errors
        print(f"Total links found: {summary.total_links}")       # All links discovered
        print(f"Unique links: {summary.unique_links}")           # Unique links (no duplicates)
        
        # Show timing information if available
        if summary.duration:
            print(f"Duration: {summary.duration:.2f} seconds")
        
        # Show error details if any occurred (limit to first 5 to avoid spam)
        if summary.errors:
            print(f"\nErrors encountered:")
            for error in summary.errors[:5]:  # Show first 5 errors only
                print(f"  - {error}")
        
    except CrawlerServiceError as e:
        # Handle crawler-specific errors (invalid URLs, network issues, etc.)
        print(f"Error: {e}", file=sys.stderr)
        
    except KeyboardInterrupt:
        # Handle when user presses Ctrl+C to stop crawling
        print("\nCrawler interrupted by user.")

def main(argv=None):
    """
    Main function (entry point)
    Args:
        argv: Command line arguments (None means use sys.argv)
    """
    # Step 1: Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Crawl a website and analyze link structure."
    )
    
    # Define command-line arguments the program accepts
    parser.add_argument("url", nargs="?", help="Base URL to crawl")
    
    # Optional arguments with default values
    parser.add_argument("-c", "--concurrency", type=int, default=10,
                       help="Number of concurrent requests (default: 10)")
    
    # -t or --timeout: how long to wait for each request
    parser.add_argument("-t", "--timeout", type=int, default=10,
                       help="Request timeout in seconds (default: 10)")
    
    # --cache-ttl: how long to cache downloaded pages
    parser.add_argument("--cache-ttl", type=int, default=300,
                       help="Cache time-to-live in seconds (default: 300)")
    
    # Step 2: Parse the actual command-line arguments provided by user
    args = parser.parse_args(argv)

    # Step 3: If user provided a URL as command-line argument, crawl it immediately
    if args.url:
        # Create configuration from command-line arguments
        config = CrawlerConfig(
            base_url=args.url,
            timeout=args.timeout,
            max_concurrency=args.concurrency,
            cache_ttl=args.cache_ttl
        )
        # Run the crawler with this configuration
        run_crawler(config)

    # Step 4: If no URL provided or we finished the first run, prompt user until they choose to exit
    while True:
        try:
            url = input("\nEnter a URL to crawl (or 'exit' to quit): ").strip()
            
            if not url or url.lower() in {"exit", "quit", "no", "n"}:
                break
                
            config = CrawlerConfig(
                base_url=url,
                timeout=args.timeout,
                max_concurrency=args.concurrency,
                cache_ttl=args.cache_ttl
            )
            
            run_crawler(config)
            
        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C or Ctrl+D (end of input) gracefully
            print("\nExiting.")
            break  # Exit the while loop

    # Return success exit code
    return 0

# This block only runs when the script is executed directly
if __name__ == "__main__":
    raise SystemExit(main())

'''
# CLI: Required vs optional arguments
# Three types of errors handled:
# 1. CrawlerServiceError: Our custom errors (bad URLs, network issues)
# 2. KeyboardInterrupt: User pressed Ctrl+C (graceful shutdown)
# 3. EOFError: User pressed Ctrl+D in interactive mode

# Two ways to use the crawler:
# 1. Batch: python app.py https://example.com
# 2. Interactive: python app.py (keeps asking for URLs)

# Exit codes tell the operating system if program succeeded
'''