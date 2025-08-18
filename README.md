# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything
we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting
started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do
and how we do it.
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

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather
  requirements,
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

This test has been created for all levels of developer, Junior through to Staff Engineer, and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a
commercial setting. You have good problem-solving abilities, a passion for writing clean and generally produce
efficient, maintainable scaleable code.

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests,
parsing HTML, and other similar tasks.

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
the trade-offs you made during the development process, and aspects you might have addressed or refined if not
constrained by time.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@2014klee, @danyal-zego, @bogdangoie and @cypherlou) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

----------------------------

# My Solution

## Environment

- Node / TypeScript
- Webstorm IDE
- Gemini Code Assist and Jetbrains AI (for brainstorming ideas around the problem, bootstrapping & giving contextual
suggestions.)

## Usage

### How to Run

```shell
npm install
npm run start
```

```shell
node ace crawler --help # for more info
node ace crawler https://www.zego.com/ --concurrency=10 --max-pages=400
```

### How to Test
```shell
npm run test
```

## Understand the Problem

I started by making sure I understood the problem. Initially, I assumed we are to load a given URL and the get all the
links on that page.
Then each of the links from the homepage, print the URL and all the links on the page.
This seemed like a simple problem, but then I noticed the phrase, _we want the crawler to run as quickly as possible without
sacrificing accuracy and compute resources._. Then it hit me that we want to recursively crawl all the links on the page.

## Tackling the Problem

I decided to bootstrap this project using AdonisJS, as it has a built-in command line tool and it's production ready.
- I then started with a simple solution, crawl the links from a simple webpage. So I described an interface of what this
Webpage should do and wrote failing tests for it. I then went ahead and wrote the code ensuring all the tests passed.
- Next, I started thinking about how to crawl each of the links on the page, at this point, I had to change the
class from a single webpage to a crawler.
This allowed me to write a recursive function that would crawl each of the links on the page.
- Taking a BFS approach, the crawler starts with a base URL, gets all the links on that page, and then recursively
- Instead of processing one page at a time, I then added controlled concurrency to the crawler. 
- Had to make some changes to make sure it's performant and also some trade-offs.
  - like using a queue head `0(1)` to dequeue instead of Array shift `0(n)`
  - separate link extraction from enqueueing for less coupling & easier testing, (at the expense of 2 iterations).

## Complex Scenarios

### Multiple Domains
- For multiple domains, we'll need per domain state management, like using a map to store the state of each domain and
it's queue, visited links, etc.
- We could also upgrade to a distributed architecture, using a message queue and database to store the state of each
domain and it's results.
- Monitor rate limits and retry requests for the different domains.

### CLI Limitations
- For realtime feedback, we need to constantly parse console output which has a performance cost.
- No easy way to pause, resume, or restart a long-running crawl.
A web API could provide a programmatic interface for starting, stopping, monitoring crawl jobs, and retrieving results,
 this is ideal for integration with other systems. We could also use a better config file format to manage concurrency
limits, politeness delays, and so on.

### Further Refinements
- Improved validations, taking into consideration the different types of links. e.g avoiding static files like images
, redirects to other domains, and so on.
- Integration tests with real websites to ensure system is working as expected.
- Respecting robots.txt and other meta tags for different type of links
- Instead of logging to console, we could use a logger to write to a file.
- Connection reuse keepAlive agents can reduce TCP and TLS overhead for multiple requests.

## Other Notes / Personal Preferences
- I avoid using comments (only where more context is needed), instead prefer to use easy to understand variable names.
