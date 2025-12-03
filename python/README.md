# python-developer-test

# Zego

## Solution

### Approach

* The task of crawling a site start from a base URL to find all URLs is as a graph traversal problem.
  URLs are nodes, links to other URLs are edges and the root node is the base URL.
* The two most popular graph traversal algorithms are BFS and DFS. My approach uses a parallelised BFS like algorithm.
* The main optimisation I used was visiting the URLs of a page in parallel.
* In ordinary BFS, neighbors are visited sequentially.
  In my approach, once a URL is observed it is placed on a queue.
  The queue is processed in parallel by workers from a pre-defined pool.
  This is a pub/sub pattern, where the workers are both publishers and consumers.
  Once the queue is empty, the site crawl has complete.

### Development Workflow

**Dev Tools:**

* PyCharm - proud user of PyCharm, I don't use any AI inside the IDE
* Google - I use this for researching problems
* ChatGPT - I use this for ideation, researching problems and writing boilerplate code to use as a starting point. It is especially good for unit tests.

**Timeline:**

* The first thing I did was implement a very simple sequential BFS in a single Python file.
  I had this working relatively quickly, the idea being to use this as a starting point and iteratively improve the solution.
* I then separated out traversing and crawling into two separate classes.
  This would make implementing optimising the traverse easier.
  I left this implementation in the `BFSTraverse` class.
* The vast majority of my time went to implementing `PooledTraverse` class:
   1. Researching the concurrency framework and pattern (discussed below)
   2. Implementing the class to not fail on edge cases, not deadlock and to terminate if any worker received an exception was challenging.
* Finally, I added robustness and refactored.

### Design Decisions

1. Parallelisation framework: `ThreadPoolExecutor/ProcessPoolExecutor` vs `asyncio/aiohttp`.

   * Visiting URLs in parallel could be implemented with separate threads/processes or as tasks in `asyncio`.
   * Most of the work done is IO (querying web pages).
   * On the other hand, if the task was to train a model per web page, most of the work would be computation.
   * The overhead of running a single thread is much higher than a single async task.
   * As such, you could scale up the amount of concurrent tasks much higher with `asyncio`.

2. Parallelisation pattern: worker pool vs unbounded amount of async Tasks.
    * Once the decision was made on the parallelisation framework, the next decision was the parallelisation pattern.
    * The amount of concurrent workers could either be bounded (worker pool) or unbounded (each URL is an async task).
    * If a site had many pages with thousands of URLs, the amount of async tasks could grow so large, the script would crash.
    * As such, a worker pool is a better option as the bound provides robustness.
    
3. Object orientated design: splitting out graph traversal and the crawler
    * Separate concerns: fetching webpages, parsing, extracting links shouldn't be in the same class as traversing a graph. 
    * Easier to test
    * Easier to reason about code

### Improvements

**Fundamentals:**

* The `fetch` method in my crawler catches `Exception`, this is a bad practise. If I had more time I would have refined this.
* I stored the final result in `_sitemap` of the crawler. A huge amount of overlapping information is stored in `_visited` of `PooledTraverse`.
  To optimise on memory it might have been better to store this all inside `PooledTraverse`.
* Add robustness: I would have written more unit tests in general. The crawler's methods likely have some edge cases I missed.
* Added pre-commit, test coverage reports.
* Added more comments throughout the code.

**Extensions:**

* My implementation covers the absolute basics for such a crawler. It is missing things such as retries, delays, timeout configuration etc.
* Implementing multiple URLs could be done by extending the traverse to start with many roots.

### Project Structure

```
.
├── crawler - source code
│   ├── crawler.py - holds a class for the crawler
│   ├── main.py - cli entrypoint
│   ├── traverse.py - holds two generic classes used for graph traversal
│   └── util.py - reusable utility functions
├── tests - PyTests
├── poetry.lock - Poetry dependency management
├── pyproject.toml - Poetry dependency management
└── README.md
```

### Requirements

- Python 3.13
- Poetry 1.8

### Running

Install Dependencies:

```bash
poetry install --sync
``` 

Run Tests:

```bash
pytest
``` 

Run Crawler:

```bash
python -m crawler.main --help
> Usage: python -m crawler.main [OPTIONS]
> 
> Options:
>   --url TEXT                      URL to crawl.
>   --workers INTEGER               Number of workers to use.
>   --log-level [critical|error|warning|info|debug]
>                                   Set log level.
>   --help                          Show this message and exit.

python -m crawler.main --url https://www.zego.com --workers 10

# Alternatively:
PYTHONPATH="${PYTHONPATH}:$PWD/crawler" python -m crawler.main --url https://www.zego.com --workers 10
``` 

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
