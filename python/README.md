<details>
<summary><h1>Original Brief</h1></summary>

# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we're only just getting started.

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

</details>

# Usage

## Prerequisites

- [uv](https://docs.astral.sh/uv/)

## Run the crawler

```bash
uv run python -m crawler https://example.com
```

### Options

```bash
uv run python -m crawler https://example.com --max-concurrency 20 --timeout 30
```

## Run tests

```bash
uv run pytest
```

## Linting & Formatting

```bash
uv run ruff check
uv run ruff format
```

## Type checking

```bash
uv run mypy src
```

# Extension
## Detailed Info
IDE - VS Code
AI - Claude Code through VS Code extension

I treated this take home like I would my day-to-day work. I mentioned this in my first interview with Charlie - my current
flow is to discuss the requirements with Claude to come up with a suitable plan, this is a back and forth with me scrutinising the plan Claude comes up with, asking it for information, coming to a decision together like I would with 
another dev. Once we have agreed on a plan, it is split up into phases so I can test, review the code, and make a commit to checkpoint in case something goes wrong or the LLM goes off track. 

Unless I'm making a PoC, I never have auto-accept edits on. It makes things take slightly longer but I like seeing the changes as they're made as it helps provide more areas for discussion as the work is being completed, rather than being surprised to end up with a load of slop right at the end when I'm about to make a PR.

I've added the plan as well but would usually not commit this.

## Design Decisions

### Async with httpx
- Async over threading for I/O-bound work
- httpx over aiohttp - cleaner API, better maintained
- httpx over requests - native async support

### Modular Architecture
- `url_utils` - pure functions for URL handling
- `parser` - pure function for HTML parsing
- `fetcher` - async HTTP with typed errors
- `crawler` - orchestration only
- Each piece testable in isolation

### BFS Traversal
- Pages closer to root crawled first
- Better for discovering site structure
- DFS would go deep into one branch before exploring others

### URL Normalisation
- Strip www (www.example.com = example.com)
- Remove fragments (#section)
- Remove trailing slashes
- Lowercase domain
- Prevents duplicate crawls

### Error Handling
- Typed errors (enum) instead of magic strings
- Continue on errors, don't crash the crawl
- Empty list for failed pages in results

## Trade-offs

### No robots.txt support
- Simpler implementation
- Trade-off: not a polite crawler, could get blocked

### No rate limiting
- Maximises speed as per requirements
- Trade-off: could overwhelm small servers

### In-memory visited set
- Simple, fast lookups
- Trade-off: memory grows with site size, won't work for millions of pages

### Console output only
- Simple, immediate feedback
- Trade-off: can't query results later, no persistence

### No retry logic
- Simpler code, faster failure
- Trade-off: transient errors cause permanent skips

### No depth limiting
- Crawls everything reachable
- Trade-off: could get stuck in infinite pagination (happened with Google)

## Future Enhancements

- Distributed crawling with message queues (Redis/RabbitMQ)
- Database persistence (PostgreSQL)
- REST API interface (FastAPI)
- robots.txt support
- Configurable rate limiting
- Retry with exponential backoff
- Depth/page count limits
- Content deduplication (hash-based)
- Better logging
- Metrics
- More complete local environment (Docker compose, local web app, etc.)
- Saving of results