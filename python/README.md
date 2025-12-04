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

## Design decisions and trade-offs

This section describes the main design choices made while implementing the crawler, the alternatives considered,
and the trade-offs that influenced the final implementation.

### Architecture overview

- Components:
  - `main.py` — CLI entrypoint, parses arguments and invokes the crawler.
  - `site_crawler.fetcher.Fetcher` — thin wrapper over the HTTP client; fetches pages and returns HTML or None.
  - `site_crawler.extractor.get_urls_from_html` — parses HTML and returns a set of normalized absolute URLs.
  - `site_crawler.crawler.Crawler` — coordinates fetching, link extraction, de-duplication, depth control and hostname validation.
  - `tests/` — pytest test-suite that exercises parsing, fetching (using fakes) and crawler logic.

This separation keeps responsibilities small and testable: HTTP details are isolated in `Fetcher`, HTML parsing in `extractor`, and crawling logic in `Crawler`.

### Concurrency model

- The crawler uses asyncio and an in-memory FIFO queue to schedule URLs. The implementation is intentionally simple:
  - The current implementation performs fetches sequentially inside an `async with aiohttp.ClientSession()` loop. This keeps the example straightforward and easy to reason about.
  - In a production scenario we would run multiple fetches concurrently (e.g., use a pool of worker tasks reading from the queue) to maximize throughput.

### URL normalization and validation

- Normalization: extracted URLs are resolved against a base URL, fragments are removed, queries are preserved, and the path is normalized to `/` if empty.

- Hostname validation: the crawler enforces an exact hostname match with the `base_url` to avoid crossing subdomains. This is the simplest and safest policy for the exercise.
  - Alternatives: allow the same registrable domain (e.g., `example.com` for `www.example.com`), or use the Public Suffix List to compare registrable domains. Those approaches are more user-friendly but more complex.

### Depth control

- The crawler supports a `max_depth` parameter: depth 0 returns only the base page; depth 1 includes direct links, etc. This provides a simple way to limit scope and resource usage.

### Testing approach

- Tests use pytest and are placed under `python/tests/`.
  - `test_extractor.py` validates URL extraction and normalization.
  - `test_fetcher.py` uses small fake async objects to simulate `aiohttp` responses without performing network I/O.
  - `test_crawler.py` and `test_crawler_crawl.py` verify `is_valid` rules and crawling behavior using injected fake Fetcher implementations.

- Trade-off: the tests prefer determinism and simplicity over full end-to-end networked tests. End-to-end tests could be added with a local HTTP server fixture.

### Error handling and resilience

- Fetcher gracefully handles exceptions and non-HTML responses by returning `None`, which the crawler skips.
- The crawler maintains a `seen_urls` set to avoid cycles and duplicate work.

### Observability and logging

- The code logs parsing/fetch errors via `logging.exception()` so problems can be diagnosed during runs. For production, structured logging and metrics (request latencies, success/failure counts) would be added.

## How to run (python3)

From the `python/` directory, install dependencies and run the crawler:

1. Create a virtualenv and install required packages:

```bash
pip install -r requirement.txt
pip install -r requirement-dev.txt  # pytest, etc. (optional)
```

2. Run the crawler (example):

```bash
python3 main.py "https://example.com/" -d 1
```

3. Run tests with pytest:

```bash
python3 -m pytest -q tests
```

## Environment & tools

- Editor: VS Code
- Python: 3.9
- Assisted: GitHub Copilot was used to help write some test cases and implement utility methods.


## Trade-offs & future work

- Concurrency: replace the sequential fetch loop with a pool of worker tasks to concurrently fetch pages from the queue.
- Persistence: use a persistent queue (Redis) and checkpointing for long-running crawls.
- Scalability: shard crawling work across multiple processes or machines.
- Observability: add structured logs, metrics, and tracing.


Distributed architecture (future)

One natural evolution is to move the crawler to a distributed architecture for large-scale crawling. A simple design:

- Publish crawl work to a Kafka topic where each message contains the URL, its depth, parent metadata and any crawl hints.
- Multiple worker services (consumer groups) read messages from Kafka, fetch pages, extract links and publish discovered child URLs back to the topic (or to a separate topic for discovered links) with updated depth and metadata.
- Keep persistent job state in a database (Postgres, Redis, etc.) so you can track progress, deduplicate work, resume failed jobs and report status to users. The DB holds canonical URL state, crawl attempts, timestamps and retry counters.

Key operational considerations: partitioning (to distribute load), idempotency and deduplication (DB unique constraints or dedupe service), backpressure handling, retry policies and observability (metrics and traces). This design enables horizontal scaling, fault-tolerance and easier monitoring of long-running crawls.

---


# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@2014klee, @danyal-zego, @bogdangoie, @cypherlou and @marliechiller) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.
