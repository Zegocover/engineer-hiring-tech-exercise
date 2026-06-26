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

## Candidate Submissions

### Rowen Robinson

#### Zego Technical Exercise

This submission is a small Node.js command line crawler. It takes a starting URL, crawls pages on the same exact domain, and prints each page with the links found on it. Links to other domains are included in the output, but they are not crawled.

#### Starting Point

The task was to build a website crawler. The original exercise mentioned Python, but this version was built in Node.js.

The crawler needed to:

- Run from the command line.
- Accept a base URL.
- Crawl only the same domain.
- Avoid crawling subdomains and external domains.
- Print each page and the links found on it.
- Run quickly without using browser tools like Playwright.
- Include tests.

#### How The Solution Was Built

I split the work into a few small parts.

First, I added the command line entry point in `src/cli.js`. This reads the URL from the command line, handles the optional concurrency setting, starts the crawler, and prints the results.

Next, I added the crawler in `src/crawler.js`. This keeps track of pages already visited and pages still waiting to be crawled. It uses a small worker-style queue so more than one page can be fetched at the same time.

Then I added `src/linkExtractor.js`. This uses Cheerio to load the HTML and read links from `<a href="">` tags.

After that, I added `src/urlUtility.js`. This handles URL cleanup and domain checks. It removes hash fragments, resolves relative links, ignores unsupported link types, and checks whether a link belongs to the same exact domain.

The first version printed everything after the crawl finished. That was not great when testing against a real website because it looked like nothing was happening. I changed it so each page is printed as soon as it is processed.

Project structure:

```text
src/
  cli.js
  crawler.js
  linkExtractor.js
  urlUtility.js

tests/
  crawler.test.js
  linkExtractor.test.js
  urlUtility.test.js
```

#### Testing

Jest was added for tests.

The tests cover:

- URL cleanup.
- Same-domain checks.
- Rejecting subdomains.
- Extracting links from HTML.
- Resolving relative links.
- Crawling a small local test server.
- Skipping non-HTML pages.
- Continuing when a page returns an error.
- Printing pages as they are processed.

I also ran `npm run coverage`. The latest run passed all tests.

#### Tools Used

- Node.js for the app runtime.
- npm for installing packages and running scripts.
- Cheerio for parsing HTML.
- Jest for tests and coverage.
- Native Node `fetch` for HTTP requests.
- PowerShell for running commands.
- Git for version control.
- Codex was used to build the plan, decide on relevant HTTP tools, assist with testing, and scan the code for missed requirements.

#### Trade-offs

The crawler does not run JavaScript on the pages. This keeps it simple and fast, but it means it will not find links that only appear after client-side JavaScript runs.

The crawler does not currently read `robots.txt`. I would add this before using it as a real production crawler.

Query strings are kept because some websites use them for real pages. This can mean more URLs are crawled, but dropping them could miss valid pages.

The command line is fine for this exercise. For a bigger crawler, I would probably use a small service with a database, a job queue, and a web page or API for viewing results.
