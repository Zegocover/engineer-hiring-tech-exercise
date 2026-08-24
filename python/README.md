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

---

# Solution

## Requirements

### Interaction

```
$ python -m crawler https://example.com
https://example.com/
https://example.com/about
https://other.example/news
mailto:team@example.com
```

For each page found per crawl, it prints each distinct URL found on it as an absolute URL, regardless of scheme or
content. "All URLs" is the distinct set — repetition is noise, not information. Crawling is limited to `text/html`
pages.

### Glossary

| Term             | Definition                                                                                                                                                                                                                                                 |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URL              | A URI as defined by [RFC 3986](https://www.rfc-editor.org/info/rfc3986/).                                                                                                                                                                                  |
| Page             | A URL returning a successful `text/html` document.                                                                                                                                                                                                         |
| URI Fragment     | The `#...` suffix of a URL; not sent to the server.                                                                                                                                                                                                        |
| Domain           | A registered domain name identifying a website.                                                                                                                                                                                                            |
| Host             | The hostname from a URL (e.g. `sub.example.com`), distinct from its registered domain and port.                                                                                                                                                             |
| Link             | A URL from a page to another resource, printed once per page as an absolute URL. We read `<a href>` only.                                                                                                                                                  |
| Crawl Politeness | Respecting access rules and request frequency. Here `robots.txt` ([RFC 9309](https://datatracker.ietf.org/doc/html/rfc9309)) controls access; pacing is out of scope. [Further reading](https://www.firecrawl.dev/glossary/web-crawling-apis/what-is-polite-crawling). |
| URL frontier     | System that holds and decides the pages that will need to be visited next.                                                                                                                                                                                 |

### Functional requirements

| ID | Requirement                                                                       |
|----|-----------------------------------------------------------------------------------|
| F1 | Accept one absolute HTTP(S) base URL as a command-line argument.                  |
| F2 | Crawl only within the same host. Subdomains are distinct hosts.                   |
| F3 | Print each page's URL and each distinct link found on it. Exit 0 when successful. |
| F4 | Exit code 1 if crawling the base URL fails.                                       |
| F5 | Exit code 2 if the input is invalid.                                              |
| F6 | Respect `robots.txt` if present and readable.                                     |
| F7 | Errors print to `stderr`.                                                         |
| F8 | Ignore URL fragments; they lead to the same page.                                 |
| F9 | Tolerate failures beyond the initial URL. Report and continue.                    |

### Non-functional requirements

| ID  | Requirement                                                             |
|-----|-------------------------------------------------------------------------|
| NF1 | Performant: run as quickly as possible. Vague but valid here.           |
| NF2 | Efficient: minimize redundant or repeated work.                         |
| NF3 | Bounded: each page returns within a timeout (5s default, configurable). |
| NF4 | Polite: respect `robots.txt` access rules.                              |

### Out of scope

| ID    | Item                      | Reason                                                                                                                                                                                              |
|-------|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| OOS1  | Dynamic content           | Requires a headless browser; such tools are excluded by the brief.                                                                                                                                  |
| OOS2  | Authentication or cookies | Simplicity. Each domain (and paths within) may have its own auth(z) model.                                                                                                                          |
| OOS3  | Handle redirects          | Simplicity. Would require validating each hop and limiting the number of redirects. Relevant since most sites redirect `http` to `https`.                                                           |
| OOS4  | Request pacing            | A static delay is simple but arbitrary; adaptive throttling requires more scope and is not standardized. More [here](https://www.firecrawl.dev/glossary/web-crawling-apis/what-is-polite-crawling). |
| OOS5  | Retry policy              | Simplicity. The CLI would need to support it, and even then it may not be one-size-fits-all.                                                                                                        |
| OOS6  | Multi-domain              | Excluded by the brief. It would also exacerbate the limitations of a single crawl.                                                                                                                  |
| OOS7  | Improved output           | Simplicity as it is not specified by the brief. No tree-like printing.                                                                                                                              |
| OOS8  | Security policies         | Assume non-malicious responses and pages fit in memory. Review other concerns with a security expert.                                                                                               |
| OOS9  | Non-`text/html` pages     | Simplicity. `application/xhtml+xml` and other HTML-like types are still real pages.                                                                                                                 |
| OOS10 | IPv6 literal URLs         | The brief scopes crawling by domain and subdomain; IPv6 literal hosts and their normalization are excluded.                                                                                         |
