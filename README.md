
# Web Crawler Task

This is an implementation in scala of a simple web crawler that can be used from CLI.

## Requirements
The following is needed to build and run:
* Java SDK - Tested with OpenJDK 21.0.9
* SBT - Sbt needs to be installed to run build. Sbt version is set up in the project build as 1.10.7 
* Scala version - Version 2.13.17 - SBT will manage relevant scala dependencies.

## Environment & Tools
* IDE - IntelliJ IDEA 2025 Community Edition
* Docker / Docker compose for local testing from CLI.
* ScalaTest for unit tests.
* Sttp with an async backend based on the java HttpClient.
* A scala scraper is used (net.ruippeixotog - scala-scraper) which wraps JSoup providing a more convenient Scala API.

To build:
```
sbt package
# build and run tests
sbt clean compile test

# build into a runnable jar
sbt assembly
# This will build a runnable jar in the target dir: ./target/scala-2.13/web-crawler-cli-app-assembly-0.1.0.jar
```

To run from CLI a shell script is included for convenience which will run the jar from the target jar built above.
```
./web-crawler.sh http://www.example.com

# Alternatively can be run through sbt
sbt "run http://www.example.com"
```

Output prints to the console to show page base URLs, and each of the child pages included indented below.
```
URL: http://localhost:8080
      |--  /pages/page1.html
      |--  /pages/page2.html
```


An example HTML site to test crawling is included that allows to traversing some links using docker & docker compose.
```
# will start nginx to server static html on port 8080
docker compose up

# to test with crawler
./web-crawler.sh http://localhost:8080
```

The Crawler will crawl all links that start from the start page, and exist on the same domain as the start page.
Once all links have been crawled within the current domain, the program will terminate.

## Design Considerations
My research into the problem showed there are a number of different ways of solving the problem, as by definition
it involves recursing into every page, so the amount of pages to visit can ramp up quickly. 
As it can be a task that runs for a while, there is a need to start recording progress as you go - For the purposes of
this exercise that means printing to the console.
To keep things fairly simple I opted for a breadth first approach, where the first page links are considered (i.e. a depth of 1),
and each further link depth level is then processed after that, until there are no links left on the same domain.

Some early thoughts:
* Track visited URLs - this is needed to avoid loops and so the app will terminate.
* Error handling - gracefully handle links that are not found, or fail for some reason. Also still track these URLs as visited to avoid
  repeatedly making failing requests.

I decided to use an async backend which used scala Futures - which is a relatively simple way of managing concurrency and therefore
improving performance so that we are not waiting for all requests and blocking up threads.

### Main Design
I separated out the main concepts so that things can be extended easily.
* PageCrawler - Main application that traverses through and tracks all links.
* HtmlLinkExtractor - The implementation provided is based on finding links, i.e. anchor tags of form `<a href="some url">link</a>`
  * This could be changed to find links using a different criteria, or non-HTML resources.
* UrlVisitStrategy - A trait that determines whether a URL should be visited. I implemented a `SameDomain` strategy.
* HttpClient - Based on Futures, but any http client could be swapped out. Error handling is very simple, the page result
    is ignored.

The actual implementation of the page crawler is based on a tail-recursive algorithm. This was a convenient way to implement
as it deals with each additional depth of links one stage at a time, which is fairly clear to read and understand.

### Trade Offs
Using an async back-end with Futures helped optimize performance a bit, so for many links on a page, the fetching of links happen
concurrently. Concurrency should also increase as it traverses through each level (assuming several links on each page). 
Because each level is resolved (with `Await`) before starting the next, there is potentially a wait before collecting all the
links. This kept the algorithm fairly simple, but it would be possible to improve performance by implementing in a way that did not
wait before starting the next level.

### Extending / Other Features

Concurrency of this could be controlled by providing a different thread pool of a desired size, rather than using the default ExecutionContext.
As Future's don't really provide much control on concurrency an effects system such as `cats-effect` could be used instead -
which would provide more options for controlling concurrency.

Other features that might be considered:
* Backoff or deliberate delay between requests to a site - to avoid overwhelming sites or upsetting site owners.
* Retry - If pages error on load, they could be tracked / retried instead of ignored.
* Use robots.txt - Implement to respect rules such as avoiding segments of a site, or requests not to crawl at all.
  This should be implemented for any crawler that were to be used on public sites.
* Maximum depth, or alternative criteria for traversing such as sub-domains.
* If traversing across multiple domains, a maximum traversal depth may need to be considered.

If this were crawling multiple domains at once it would be fairly easy to adapt this to accept multiple URLs.
If crawling multiple domains, tuning of concurrency may need to be further considered.
The way the information is output would need to be changed to make it clear what domain the information is for -
this is one of the shortfallings of using CLI as displaying a lot of information isn't really well suited to this.
An alternative might be to create report files (e.g. in HTML) that could be uploaded somewhere - these would be easy
to split out by domain so would be more suited to the multi-domain scenario.
