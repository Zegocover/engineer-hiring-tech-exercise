# Notes

Created using Gemini. Prompts used:

* Create a CLI tool in Python. It is a web crawler which accepts a URL on the command line. Each URL it finds should be printed to the terminal. It should only pring any given URL once. It should not crawl outside the domain of the given URL. The code must be unit testable. It should leverage aiohttp to allow parallel execution of crawling code. Include the tests. Follow best practices such as SOLID, DRY and KISS.
* Update the crawler to respect robots.txt

# Simple Web Crawler

A simple, asynchronous web crawler CLI tool built with Python, `aiohttp`, and `BeautifulSoup4`. It crawls a given URL, extracts all links within the same domain, and prints each unique URL found to the terminal.

## Features

*   **Asynchronous:** Leverages `asyncio` and `aiohttp` for efficient, parallel crawling.
*   **Domain-Constrained:** Only crawls URLs within the initial domain provided.
*   **Unique URLs:** Prints each discovered URL only once.
*   **CLI Interface:** Easy to use from the command line.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/simple-web-crawler.git
    cd simple-web-crawler
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install .
    ```
    This will install `aiohttp`, `beautifulsoup4`, and the `web-crawler` command-line tool.

## Usage

To start crawling, simply run the `web-crawler` command followed by the starting URL:

```bash
web-crawler <start_url>
```

**Example:**

```bash
web-crawler http://quotes.toscrape.com
```

### Options:

*   `-c`, `--concurrent`: Maximum number of concurrent requests (default: 5).

    ```bash
    web-crawler http://quotes.toscrape.com -c 10
    ```

## Development

### Running Tests

To run the unit tests, make sure you have installed the development dependencies (including `pytest` and `pytest-asyncio`):

```bash
pip install ".[dev]" # Or just `pip install pytest pytest-asyncio`
pytest
```


## Project Structure

```
.
├── crawler/
│   ├── __init__.py
│   ├── crawler.py          # Core crawling logic
│   └── main.py             # CLI entry point
├── pyproject.toml          # Project metadata and dependencies
└── README.md
```
