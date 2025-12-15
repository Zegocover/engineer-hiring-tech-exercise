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
4. Add us (@2014klee, @danyal-zego, @bogdangoie, @cypherlou and @marliechiller) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.

# Submission Summary

## Code Documentation

This project uses [SBT](https://www.scala-sbt.org/), and you can build it using these commands;

```bash
# compile the main code
sbt compile 

# run test suite
sbt test
```

You can run the crawler itself using SBT. As an example you can use my personal website (https://www.bumblebyte.co.uk, a
small static site) to test. I also tested with larger sites (e.g. https://news.bbc.co.uk) but due to the size you will
need to cancel the crawling manually (with Ctrl-C).

```bash
sbt clean "run https://www.bumblebyte.co.uk/"
```

[`WebCrawler`](src/main/scala/zego/tech/exercise/WebCrawler.scala) implements the main crawling loop and has some
comments describing the behaviour.

## Approach

With a task like this I usually prefer to focus on the smallest solution that satisfies the brief. To simplify the
requirements I decided to do the following;

* Implement a simple, synchronous request loop.
* Perform limited crawling by only looking for link attributes in HTML documents.

As stretch goals I also implemented redirect handling, as well as robots.txt validation. I felt these two things were
important as they could prevent the crawler from working properly. For example, the crawler could redirect from `/` to
`/index.html`, and then crawl `/index/html` again if encountered without the redirect. A site could also identify and
reject the crawler from further requests if it started crawling forbidden URIs.

I used the following libraries;

* STTP - a robust HTTP library with multiple backends, testing support.
* jfiveparse - a Java based HTML5 parser, I chose this because I liked the API more than some Scala native solutions.
* scalatest - testing framework

To complete this task I used IntelliJ IDEA, I didn't use an AI assistant but I do occasionally use ChatGPT to debug
small code snippets.

## Possible Enhancements

There are a couple of enhancements that I would make if I spent more time working on this project.

### Asynchronous Crawling

The current design uses a synchronous loop to execute requests. There's two ways this could be improved;

1. Fan out requests and use an asynchronous HTTP client backend instead. This would improve the speed without having to
   implement coordination logic for searched URIs.
2. Use fully asynchronous workers, this would be easy to achieve by using a dedicated streaming framework instead. You
   would still need to implement some kind of coordination but again that's easily supported in some frameworks.

The drawback there is that some sites might start to rate-limit or deny excessive crawler requests so this would also
need to be considered.

### Smarter Crawler Logic

At the moment the crawler parses any response for HTML. This doesn't consider the content-type, or other request
information that might be available to us (like request headers). It also causes an issue on pages that make heavy use
of JavaScript for HTML rendering. If a response isn't HTML it's quietly discarded. Similarly, if we encounter a 4xx or
5xx the request is not retried.

The current crawler accumulates both the upcoming URIs and the searched URIs, for large sites this might start to
consume a lot of memory. We could store more specific path information rather than full URIs, as well as nest related
paths to reduce the size.

### Improved Debugging

It would be great to add logging to the crawler to understand the decisions it makes about what it should / should not
crawl. This would make it easier to diagnose issues when dealing with more complex sites. It would also be great to have
a more comprehensive test suite that provides more realistic examples of web page responses. This could also use a
dedicated test server to improve the realism of the tests.
