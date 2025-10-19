## How to achieve efficient parsing of the URLs?

I have a function which will crawl any single website and print every link it finds,
formatted as an absolute link.

Website crawlers cannot only concentrate on trying to access the links as fast as possible,
there are real challenges to not overload a service, handle variety of errors gracefully and be
intelligent about the speed and retries of trying to access a page. It's quite simple to add
threading to increase the speed of a crawler, as a lot of the processing is I/O bound, but in reality
this won't make the crawler faster.

Use Singleton pattern to store the shared resources - in this POC it would be request session and domain, but otherwise, it could be database
connection or proxy pool.

Use the Producer - Consumer pattern to crawl the links concurrently.

1. only continue to crawl the links which are part of the same domain (challenge requirement)

- [ ] write the decision process as a separate function (accepts only absolute links, validates it, so no `#` allowed)
- [ ] test this function to ensure that it would only decide to continue with the same domain

This could still result in a non-stop recursive loop

2. keep track of the links which have been crawled

Make sure to store both links to be visited and also those which have been visited to avoid duplication

- [ ] add urls_to_visit and visited_urls lists
- [ ] test that these would only contain the URLs with the correct domain

3. Throttle the requests

In order to avoid overloading a service and the web scrapper failing, implement an optional timeout attribute to the crawl function;
this attribute takes an integer (milliseconds)

- [ ] use the same session `requests.Session()` across a single crawling session to reduce the pressure on target server

How to decide when to use the throttle and by how much?

4. Handle errors

The status response could be not 200, how to handle that?
- 4XX errors - most likely 404 - skip over them and head to next link, add the link to visited links
- 429 and 5XX errors - retry the crawl and set exponential timeout (3 retries - each time increment the throttle twofold, start at 5 seconds);
a nice to have would be to add a reader for the `Retry-After` header
Similarly, websites wary in the way the throttle requests, so a more intelligent algorithm could be set up to track this behaviour




- [ ] check the `robots.txt`


## Nice to haves

Create a microservice architecture 

- TO DO - create an image of the architecture and add some example technologies I'd use
- potential to restart a job

## Challenges of the current design

- While CLI could be absolutely fine for certain types of users to start a web crawler task,
as an end product it is not great.

Printed out links cannot be used for much else, as they are difficult to parse, analyse and use.
Scrollback buffer size affects how many links user would be able to see.

- Lack of authentication and authorization


