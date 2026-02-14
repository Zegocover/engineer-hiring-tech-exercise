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
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou and @marliechiller) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

**Solution Overview**
This repository contains a CLI crawler that accepts a base URL, fetches pages within the same domain, and prints each page URL along with all discovered links on that page. It schedules only same-domain links for crawling, while still printing every link found.

**Disclaimer**
I generally prefer to keep documentation and code in separate artifacts, but I included all documents in this repo to provide full context for the exercise.

**High-Level Architecture**
```
CLI Entry Point
      |
      v
   Crawler (orchestrator)
    |   |   |
    |   |   +--> Output formatting (after crawl)
    |   |
    |   +------> Work Queue (BFS) + Scheduled/Visited sets
    |
    +------> Worker (fetch + parse + link discovery)
```

**How To Run (Poetry)**
1. `cd python/crawler`
2. `poetry install`
3. `poetry run crawler https://example.com`

**How To Run (Without Poetry)**
1. `cd python/crawler`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python -m crawler https://example.com`

Notes: `requirements.txt` is generated via `poetry export -f requirements.txt --output requirements.txt --without-hashes`.

**Toy Examples**
1. `poetry run crawler https://example.com --max-urls 5`
2. `poetry run crawler https://example.com --batch-size 3 --timeout 5`
3. `poetry run crawler https://example.com --output out.txt`
4. `poetry run crawler https://example.com --output out.txt --quiet`

Output format notes: stdout omits page indices; the output file includes `[n]:` page indices. Blank lines separate pages in both.

**Tests & Quality Checks**
1. `poetry run pytest`
2. `poetry run ruff check src tests`

**Design Decisions & Trade-Offs**
- BFS traversal with an in-memory queue for fairness and simple deduplication.
- Separate sets for `_scheduled` and `_visited` to avoid duplicate work before fetch completion.
- Async I/O with `aiohttp` and batching for throughput without overwhelming resources.
- Worker extracts all links, but only same-domain links are used for crawling.
- Output is emitted after the crawl completes to keep I/O out of the hot path.
- Retries are handled in `Crawler` by re-queueing failed URLs to keep Worker simple.

**Assumptions**
- The base URL includes scheme and netloc.
- Only exact netloc matches are crawlable, so subdomains are excluded.
- Memory can hold the scheduled/visited sets for the crawl.

**Known Issues / Risks**
- The `max_urls` limit prevents scheduling more URLs, but in-flight or already queued pages can still be fetched.
- Retries are handled by re-queueing failed URLs; exponential backoff and jitter are not implemented.
- Redirects to external domains are treated as errors; some sites may redirect between equivalent hosts.

**What’s Weak / Incomplete (And Why)**
- **Deferred output**: Results are printed after the crawl completes. This keeps console output clean (no interleaving with logs), but it is less memory‑efficient and provides slower feedback for large crawls. A streaming printer could emit per‑page results while still writing logs to stderr, but we chose a single final output to keep the CLI experience clean.
- **Minimal retry policy**: Retries simply re‑queue failed URLs without backoff or jitter. Adding retry delays would increase complexity and is more valuable in a long‑running service than in a short‑lived CLI tool. We kept it simple for now.
- **Light URL canonicalization**: Only basic normalization is applied (e.g., fragments removed). More aggressive canonicalization (query normalization, trailing slash rules) can change semantics and adds complexity. The exercise favors clarity over exhaustive URL rewriting.
- **In‑memory results**: All results are stored in memory, which is fine for a bounded crawl but becomes a bottleneck at scale. A persistent store (SQLite, file‑backed queue) would be necessary for very large crawls or multiple seed URLs, but was intentionally out of scope.

**Complexity & Bottlenecks**
- Time complexity is O(V + E) where V is pages visited and E is links processed per page.
- Space complexity is O(V + E) due to stored results and link lists.
- Bottlenecks: network latency, HTML parsing, and large link sets per page.
- Potential optimizations: streaming output, limiting stored links, and incremental persistence.

**Logging**
- Progress logs are emitted during the crawl (batch size, queue length, scheduled/visited counts).

**Tools & Workflow**
**Environment**
- IDE: VS Code
- Assistant tools: ChatGPT (brainstorming) and Codex (implementation partner)

**Process**
1. **Requirement capture**: Read the assignment and documented explicit requirements, assumptions, and risks in `python/docs/notes.md`.
2. **Exploration & ideation**: Used ChatGPT to brainstorm approaches, edge cases, and possible architectures.
3. **Design**: Wrote a structured technical design in `python/docs/zego_crawler_technical_design_document.md`, clarifying components, responsibilities, and constraints.
4. **Implementation**: Used this Codex chat to iteratively implement the crawler, tests, logging, and output behavior, validating each change against the requirements.
5. **Refinement**: Adjusted naming, boundaries, and test coverage based on feedback and observed behavior.

**Why this approach**
- Keeps a clear paper trail from requirements → design → implementation.
- Makes trade-offs explicit and reviewable.
- Ensures test coverage evolves alongside behavior changes.

**Open Tasks**
- Push code and add collaborators per the test instructions.
- Consider more robust retry policies (backoff, jitter) and better domain matching (public suffix list).
