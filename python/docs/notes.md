# Explicit Requirements:
- print each url it finds + the urls in the page for the url
- sould be contained to a singled domain (avoid crawling subdomains or other domains)
- crawler should run as quick as possible without compromising accuracy and compute resources
- avoid scrapy or playwright

# Assumptions I'm making:
- Not print repeated pages (avoid circular url paths)
- should be resilient to transient errors (prob skip and mark for retry add to queue again; after retries print error)

# Here is my technical decisions:
- In-memory Queue:
  - At every loop select a BATCH on next pages to visit in parallel.
  - Once the batch is finished perform validations + mark visited + add to queue.
  - BFS approach.
- Libs: AsyncIO + beautifull soup + aiohttp (clear concurrency model + limit configuration) + urllib
- CLI script: 
  - Params: 
    - the url required; 
    - output file (the idea is to allow a json/yml/file as an output) as optional
    - MAX BATCH SIZE to controll parallelism optional with default (min-max considering machine resources); 
    - MAX DEPTH/URLS SIZE optional with default (need to think better, the idea is to avoid memory issues);
- Classes:
  - Main: holds cli entry point
    - Unit tests: params checnking and validations + functional behavior: can instantite Crawler
  - Crawler: represents the single instace of a crawler for a single web site. Holds the queue logic and the process for a particular seed url.
    - Unit tests: params checnking and validations + functional behavior of the queue (dependencies can be mocked).
  - Worker:  do the work of visiting a url + parsing the html + discovering new urls.
    - Printing will not occur here. Avoind sideeffects inside async code.
    - Unit test: params checking and validations + functional behavior of: get url html; parsing the html; discovering urls
- Poetry: will provide project scaffold, package management, easy to use cli.
- Error handling: best-effort crawl + explicit Result type + small transient retry + record failures
- Architecture: choose per-URL job (b); optionally offload parsing if needed

# Design principles:
- Main principles:
  - KISS and YAGNI and least surprise principles
  - FP over OOP when simplicity is not compromised
  - Tests: aim for correctness and making requirements explicit, not coverage
- Secondary principles:
  - DRY, SOLID, Clean Code, Clean Architecture

# Decision to consider optional improvements:
- More granular Worker: UrlPageWorker + HtmlParserPagerWorker + UrlDiscoveringPageWorker
  - Model a queque with a pipeline of small jobs to do (more complex but could allow more to be done in parallel)
- Use sqlite (local db): (more complex but could allow solution to scale to handle multiple urls at the same time; recovery + persistent state; no memmory issues)
- Streamlit UI: simple UI with a simple form to trigger the crowling and another page for seeing the results + download report option. More work but better user experience. 
