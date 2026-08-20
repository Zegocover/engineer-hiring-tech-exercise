# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it.
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="../doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="../doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="../doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="../doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team

Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative
team of engineers that thrive on challenge and innovation.

### How We Work

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather requirements,
  deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
- **Problem Solving & Innovation** - We encourage analytical thinking and a proactive approach to tackling complex
  problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
- **Continuous Learning & Growth** - At Zego, we provide engineers with abundant opportunities to learn, experiment and
  advance. We positively encourage the use of AI in our solutions as well as harnessing AI-powered tools to automate
  workflows, boost productivity and accelerate innovation. You'll have our full support to refine your skills, stay
  ahead of best practices and explore the latest technologies that drive our products and services forward.
- **Ownership & Accountability** - Our team members take ownership of their work, ensuring that solutions are reliable,
  scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?

This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a commercial setting. You have good problem-solving abilities, a passion for writing clean and generally produce efficient, maintainable scaleable code.

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## The objective

This exercise is intended to allow you to demonstrate how you design software and write good quality code.
We will look at how you have structured your code and how you test it. We want to understand how you have gone about
solving this problem, what tools you used to become familiar with the subject matter and what tools you used to
produce the code and verify your work. Please include detailed information about your IDE, the use of any
interactive AI (such as Copilot) as well as any other AI tools that form part of your workflow.

You might also consider how you would extend your code to handle more complex scenarios, such a crawling
multiple domains at once, thinking about how a command line interface might not be best suited for this purpose
and what alternatives might be more suitable. Also, feel free to set the repo up as you would a production project.

Extend this README to include a detailed discussion about your design decisions, the options you considered and
the trade-offs you made during the development process, and aspects you might have addressed or refined if not constrained by time.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou, @marliechiller and @ZEGODiogoAlves) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.


# Solution notes

## How to run

The project requires Python 3.10 or later. From the repository root, create
and activate a virtual environment, then install the application and its test
dependencies:

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

The crawler can then be run through the installed `site-crawler` command or as
a Python module:

```bash
site-crawler https://example.com
python -m site_crawler https://example.com
```

### Parameters

The positional `base_url` is the starting page. It may include `http://` or
`https://`; if no scheme is supplied, HTTPS is used. Only pages on the exact
same hostname are crawled. Subdomains and external domains are skipped.

Optional arguments:

- `--depth N` limits the crawl to `N` levels from the starting page. The
  default is unlimited depth. `N` must be a positive integer.
- `--concurrency N` controls the maximum number of pages fetched at once. The
  default is `5`, and `N` must be a positive integer.
- `--include-duplicates` prints repeated links when the same link appears
  more than once on a page. By default, links printed for each page are unique.

Examples:

```bash
# Crawl from a hostname, using HTTPS by default.
site-crawler example.com

# Crawl the starting page and the next two levels.
site-crawler https://example.com --depth 2

# Use ten concurrent requests and preserve duplicate links in page output.
site-crawler https://example.com --concurrency 10 --include-duplicates
```

For all available options, run:

```bash
site-crawler --help
```

### Running tests

Run the complete test suite from the `python` directory:

```bash
python -m pytest
```

Run a specific test module when working on one part of the crawler:

```bash
python -m pytest tests/test_cli.py
python -m pytest tests/test_parser.py
python -m pytest tests/test_url_policy.py
```

Run the configured lint checks with:

```bash
ruff check .
```

## Design and structure

The crawler is split into three small responsibilities:

- `cli.py` owns argument parsing, crawl orchestration, breadth-first depth
  handling, bounded concurrency, and console output.
- `parser.py` owns HTTP requests, response validation, redirect handling,
  retries for HTTP 429 responses, and HTML link extraction.
- `url_policy.py` owns the crawl boundary. It accepts only HTTP(S) URLs on
  the exact base hostname, removes fragments, and normalizes URLs without a
  path to `/`.

The initial URL and every discovered link pass through the same policy before
being queued. A `visited` set prevents repeated fetches, including links that
differ only by a fragment or by the presence of a trailing slash on the root
URL.

## Options considered

`httpx.AsyncClient` was chosen over synchronous `urllib` calls because a crawl
is dominated by network waiting. A shared client allows connection reuse, and
the semaphore limits the number of concurrent requests. The default concurrency
of five is deliberately conservative: it improves throughput without creating
an unnecessarily aggressive load on the target site. It can be changed with
`--concurrency`.

BeautifulSoup was chosen for HTML parsing. A regular expression would be shorter
but would be fragile around malformed markup, quoted attributes, and HTML
entities. Scrapy and Playwright were not used.

The crawl proceeds in breadth-first levels. This makes `--depth` predictable:
the base page is level zero, its links are level one, and so on. Pages within a
level are fetched concurrently and printed as they complete. That maximizes
responsiveness, so output order is intentionally nondeterministic when request
completion order differs. The crawler still guarantees that each normalized
URL is fetched at most once.

Redirects are handled explicitly rather than enabling automatic redirects.
Each redirect target is resolved relative to the current URL and checked with
the same host policy before it is requested. This prevents an allowed page
from redirecting the crawler to another domain or subdomain.

## Error handling and verification

The crawler skips non-HTML responses, reports HTTP and request errors for an
individual page, and continues with other queued pages. HTTP 429 responses are
retried up to three times using `Retry-After` when available, otherwise an
exponential backoff is used. Redirect chains are capped to avoid loops.

The tests cover CLI validation, depth limits, concurrency, duplicate visits,
URL policy boundaries, relative links, fragments, duplicate links, malformed
redirects, cross-domain redirects, same-host redirects, timeouts, retries,
unusual ports, and real `httpx.Response` objects through `MockTransport`.
The project is checked with:

```text
cd python
python -m pip install -e '.[test]'
python -m pytest
ruff check .
```

## Limitations and future work

This is intentionally a single-process crawler for one exact hostname. It
does not execute JavaScript, discover links generated by client-side code, or
interpret sitemap files. It also does not yet implement robots.txt handling,
response-size limits or authentication. Output is non-deterministic.

The state is not stored - if a crawl is interrupted it will need to be run
from the start.

## Development workflow

Development and review were carried out in VS Code on WSL using the Python
virtual environment in the repository. GitHub Copilot was used interactively
to help inspect the existing code, identify edge cases, propose focused tests,
and review the implementation against the exercise requirements. Changes were
validated locally with pytest and Ruff; network-dependent behavior was tested
with mocked HTTP responses so the test suite remained repeatable and did not
depend on an external website. The CLI was called manually to test against 
https://crawler-test.com/.