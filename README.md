# python-developer-test

# Zego

## About Us
At Zego, we understand that traditional motor insurance holds good drivers back. 
It's too complicated, too expensive, and it doesn't reflect how well you actually drive. 
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig workers to everyday car drivers, our customers are the driving force behind everything we do. 
We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values
Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it. 
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team
Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products 
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative 
team of engineers that thrive on challenge and innovation.

### How We Work
* Collaboration & Knowledge Sharing - Engineers at Zego work closely with cross-functional teams to gather requirements,
deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
* Problem Solving & Innovation - We encourage analytical thinking and a proactive approach to tackling complex
problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
* Continuous Learning & Growth - At Zego, there's loads of room to learn and grow. Engineers are encouraged to
refine their skills, stay updated with best practices, and explore new technologies that enhance our products and services.
* Ownership & Accountability - Our team members take ownership of their work, ensuring that solutions are reliable,
scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?
This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a commercial setting.
You have good problem-solving abilities, a passion for writing clean and generally produce efficient, maintainable scaleable code. 

## The test
Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## The objective
This exercise is intended to allow you to demonstrate how you design software and write good quality code.
We will look at how you have structured your code and test cases. We want to understand how you have gone about
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
4. Add us (@2014klee, @danyal-zego, @bogdangoie and @cypherlou) as collaborators and tag us to review.

# 👋 Hello
Thanks for checking out my submission.

# Setup
This project uses [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) and [Docker](https://docs.docker.com/desktop/setup/install/mac-install/)
### Getting Started
1. Setup project
```shell
poetry install
poetry env activate
```
2. Run the tests
```shell
inv test
# You might get an initial failure from the Fetcher while docker sets itself up. Rerun the test and you should be ok.
``` 
3. Run the application
```shell
python -m crawlspace <http://some-cool-website.com>
```


# Design Decisions and Trade-offs
I have made my development notes available in the [NOTES.md](NOTES.md) file.

## Initial Thoughts on the Test

My initial assessment of the crawling task highlighted the inherently asynchronous nature of network operations. Fetching content from websites is I/O-bound, while the subsequent parsing of the HTML is more CPU-intensive. This distinction immediately suggested that concurrency would be crucial for performance.

## Asynchronous Approach with `asyncio`

I opted to leverage Python's built-in `asyncio` library for handling the network requests. Its maturity and integration within the Python ecosystem made it a natural choice. While introducing concurrency always carries the potential for deadlocks and race conditions, I decided to focus on the core asynchronous fetching logic provided by `asyncio` for this exercise, acknowledging that more explicit concurrency control patterns could be explored in a more time-unconstrained scenario.

## Collaborative Parsing with Gemini and TDD

The implementation of the HTML parsing logic using `Beautiful Soup 4 (bs4)` was a collaborative effort with the Gemini language model through an adversarial Test-Driven Development (TDD) process. I found the back-and-forth of writing tests and then reviewing the generated code to be quite engaging, even if the manual copying could be a bit tedious. This process did ensure a thorough reading of the code. I consciously avoided using more automated code generation tools like Copilot, as I believe it's important to maintain a strong understanding of the code being produced and avoid the temptation of accepting potentially suboptimal suggestions too easily.

## Architectural Design: The Facade Pattern

To structure the application, I employed a facade pattern with the `Crawler` class. This class serves as a single point of interaction, hiding the underlying complexity of the `Fetcher`, `Parser`, and `URLFilter` components. The `Fetcher` (responsible for making HTTP requests) and the `Parser` (responsible for extracting URLs from HTML) were designed as injected dependencies, promoting modularity, testability, and the potential for swapping out implementations. The `URLFilter` is instantiated by the `Crawler` to manage which URLs should be processed.

## URL Filtering Logic

The `URLFilter` plays a critical role in ensuring the crawler adheres to the specified constraints. It implements several key rules:

- Preventing the revisiting of URLs to avoid redundant work and infinite loops.
- Restricting crawling to URLs within the initially provided base domain.
- Excluding URL fragments, as these typically point to specific sections within the same page.
- Normalizing URLs by disregarding the scheme (`http` vs. `https`) during comparisons.

The behavior of the `URLFilter` was primarily defined through test cases developed in collaboration with Gemini using adversarial TDD.

## Handling Multiple Domains

My initial thought on extending the crawler to handle multiple domains concurrently would be to simply instantiate multiple independent `Crawler` objects, each configured with its own `base_url`. This approach would naturally leverage the asynchronous fetching capabilities already in place and respect the current concurrency settings of the `Fetcher`.

For a more scalable solution when dealing with a large number of domains, I would consider making the `Parser` a shared singleton class. This singleton would manage parsing jobs from different `Crawler` instances, calling back with the results. This could lead to more efficient resource utilization by avoiding redundant instantiation of parser objects. The individual `Crawler` instances would then primarily focus on the networking and URL harvesting aspects for their respective domains.

## Areas for Future Refinement

Given more time, there are several aspects of the crawler I would have liked to address and refine:

- **Expanding File Type Support:** The current implementation only processes HTML files. I would have extended it to handle other content types, such as plain text files, potentially using regular expressions for URL extraction.
- **Comprehensive Tag Analysis:** The parser currently only considers `a`, `link`, and `img` tags. I would have expanded its scope to extract URLs from a wider range of HTML tags as defined in the HTML specification.
- **Implementing a Chain of Responsibility for File Handling:** To manage the processing of different file types more elegantly, I would have considered implementing a Chain of Responsibility pattern. This would allow for the addition of new file processing strategies without modifying the core crawler logic.
- **Real-Time Monitoring with FastAPI:** A significant enhancement would be to wrap the crawler within a FastAPI server. This would allow for a real-time view of the discovered URLs as they are being gathered, providing valuable insight into the crawling process and potentially offering an API to interact with the crawler.

These potential extensions reflect my thinking about building a more robust, scalable, and user-friendly web crawling solution.

