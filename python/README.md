# python-developer-test

## Planning

See the working plan in `PLAN.md`.

## Running

Install dependencies and run the crawler with uv:

```bash
uv sync
uv run crawler https://example.com
```

CLI usage:

```
usage: crawler [-h] [--profile {conservative,balanced,aggressive}]
               [--output {text,json}] [--output-file OUTPUT_FILE]
               [--robots {respect,ignore}] [--user-agent USER_AGENT]
               [--strip-fragments | --no-strip-fragments]
               [--only-http-links | --no-only-http-links]
               [--only-in-scope-links | --no-only-in-scope-links] [--verbose]
               base_url

positional arguments:
  base_url              Starting URL to crawl (http/https).

options:
  -h, --help            show this help message and exit

Output:
  --output {text,json}  Output format (written to a file).
  --output-file OUTPUT_FILE
                        Output file path; defaults to output.txt or output.json
                        based on format.

Crawl options:
  --profile {conservative,balanced,aggressive}
                        Preset crawl limits (max pages/depth, concurrency,
                        timeouts, rate).
  --robots {respect,ignore}
                        Whether to respect robots.txt rules.
  --user-agent USER_AGENT
                        User-Agent header value for HTTP requests.
  --strip-fragments, --no-strip-fragments
                        Strip #fragments from extracted links (default: true).
  --only-http-links, --no-only-http-links
                        Only include http/https links in output (default: true).
  --only-in-scope-links, --no-only-in-scope-links
                        Only include in-scope links in output (default: false).
  --verbose             Enable verbose (debug) logging.
```

## Design decisions and trade-offs summary

This README includes a short summary of the key design decisions, options considered, and trade-offs. The full working notes, rationale, and extended discussion live in `PLAN.md`.

### Architecture and flow
I used an async, queue-driven design with a scheduler and worker tasks. The scheduler is the single place that handles scope checks, deduplication, robots policy, and enqueuing. Workers focus on fetching, parsing, and emitting links. This split keeps URL governance centralised and avoids locks in hot paths, while still allowing concurrency for I/O-bound work.

### Scope rules
The crawler only accepts URLs on the exact host of the base URL. This matches the prompt requirement to exclude subdomains. I previously considered eTLD plus one, but removed it to keep behaviour strict and aligned with the spec.

### URL handling and normalisation
I retain query strings because they can encode page-specific content. Fragments are stripped by default because they are typically in page anchors, and they can explode the URL set. Trailing slashes are normalised for dedupe to reduce duplicates, and the output uses the normalised page URL to keep results stable across runs. Link filtering for fragments, scheme, and in-scope output is configurable.

### Fetching and retries
The fetcher uses `aiohttp` with a shared session, explicit timeouts, and typed error handling for redirects, 429, retryable and non-retryable failures. For retryable errors I use exponential backoff with a cap, and honour Retry After when present. I cap retry attempts to avoid infinite loops.

### Redirects
Redirects are not auto-followed. The worker raises a redirect error and the redirect target is sent back to the scheduler as a candidate. This preserves consistent scope and robots checks in one place.

### Output format and streaming
Text and JSON outputs are supported via a renderer interface. Output is streamed to avoid large memory usage. The renderer now owns a lock so concurrent writes from workers do not interleave.

### Shutdown and determinism
I added a safe shutdown that waits for both queues to drain and then stops the workers. This avoids stopping while work is still in flight. For stability, the page URLs written to output are normalised so the result set is consistent across runs.

### Testing strategy
I focused on fast unit tests for URL parsing, scoping, parsing, scheduling, fetching, and rendering. There is a minimal integration-style test for `app.run_async` to verify wiring. Tests use fixtures rather than live network calls where possible.

### Tooling, IDE, and AI usage
- **IDE:** Visual Studio Code.
- **AI assistance:** Codex (ChatGPT) was used as a collaborative assistant for design discussions, suggestions, refactors, and test coverage improvements. Final decisions and changes were applied by me. Towards the end of the exercise, Codex was asked to complete a thorough code review, and changes were made based on the suggestions.
- **Formatting and linting:** Black and Ruff were configured and used to keep style consistent and catch common issues.
- **Workflow:** I used uv for dependency management and pytest for tests. The project uses a standard `src/` layout with an isolated `tests/` directory. Notes and extended reasoning live in `PLAN.md`.

### Deferred items
I left sitemap discovery, per-path crawl delay, and a writer queue as could-have items to keep scope tight. JS rendering and multi-domain crawling are explicitly out of scope for this submission.

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
4. Add us (@2014klee, @danyal-zego, @bogdangoie, @cypherlou and @marliechiller) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.
