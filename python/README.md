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

## The Process

### To run the program
- Install requirements from [requirements.txt](requirements.txt)
- run `python main.py <url>` with a url of your choice

### Tools and libraries used
- [Pycharm](https://www.jetbrains.com/pycharm/)
- Python 3.12.11 ran in a virtual environment
- [Beautiful Soup](https://beautiful-soup-4.readthedocs.io/en/latest/)
- [TldExtract](https://pypi.org/project/tldextract/) to compare urls
- [AIOHttp http client](https://docs.aiohttp.org/en/stable/client.html)
- Python standard library (Collections, Asyncio, urllib)
- Pytest for testing

### Testing
- Manual testing against multiple sites(https://monzo.com, https://realpython.github.io/fake-jobs/, https://crawler-test.com/) and then confirming that the output contained unique keys that belonged only to the baseurl as well as all the associated keys being urls


### How I went about understanding the problem
In the past I've worked on a similar take home project, so I'm familiar with common libraries in python used to parse html and pull out urls (in this case [Beautiful soup](https://beautiful-soup-4.readthedocs.io/en/latest/#)).
To refamiliarise myself with the concept of a web scaper/crawler, I looked at [tutorials that exist on real python](https://realpython.com/beautiful-soup-web-scraper-python/) to do with building scrapers that pull out content as well as urls. 

### How I built the solution
After looking at the problem and doing my reading, my first thoughts were that a solution would require:

- The ability to process pages concurrently specifically using asyncio since the main blocker here is I/O which non blocking async is very useful for. Also I've used async python a lot during my career vs multithreading/multiprocess. 
- Utils to parse the html and pull out all of the urls found
- A crawler implementation which maintains state of urls processed, urls to be processed and a dictionary that stores all the urls found under a given page

My first passthrough was to create a version that processes each url sequentially but using asyncio to run the process to make it easier to switch to async processing of urls. 

Starting with [main.py](main.py), we created the code to parse input given when running the program as well as kicking of an event loop and kicking off the parser task. 

I then focussed on creating the [http client](clients/client.py) and [utils](utils) required to facilitate the scraping. These were done as modules as there was no inherent state needed for extracting urls from html or making a get call to urls. 

For [clients.py](clients/client.py), we use aiohttp client to process a get for a specific url, check if the content_type of the response contains "text.html" and then return the body as a string. If it's not an html body, we return an empty string for now. 

The first util was [html_parser.py](utils/html_parser.py) which uses beautiful soup to process the html. The second was [urls.py](utils/urls.py) which contains three functions

- `clean_url` which takes a url and returns a sanitized version without fragments, query strings, trailing slashes as well as removing `www.`
- `is_relative_url` checks for urls that start with a `/` to allow us to understand when urls are relative
- `within_subdomain` takes the a url and the base url and checks that the fully qualified domain name matches that of the base url provided when starting the program.

Once established, I started creating a [parser class](parser.py) that used sets to manage things to process vs what had been processed as well as a dict to store the urls found per page (key: list). 

After running the code against some sites to see that it would parse through urls, I worked on allowing the code to work concurrently instead of sequentially. To do this, I had to switch to using a [Queue](https://docs.python.org/3/library/asyncio-queue.html#queue) to hold the urls to be processed and spawn a number of worker tasks on the event loop to continuously process the queue.

At first I tried to have the workers run as long as the queue wasn't empty but that just ended up killing every worker bar one essentially sequentially processing the urls. I switched this to having the workers run forever and having the parser maintain a list of workers. The process function on the parser now spawns the tasks and then awaits the [Queue join function](https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue.join)  which will block until all items in the queue have been processed. After the join function returns, we pretty print the dictionary and then cancel the tasks to end which allows the program to proceed to the `loop.close()` in main.py.

After running the code against a few sites, I noticed a few errors popping up when it came to what urls were being added to the queue. Turns out I had ignored the fact that the urls that could be found on a given page could be more than ones with the schemes `https, https and ""`. To handle this, I updated the [urls.py](utils/urls.py) `within_subdomain` function to check that the schemes are only within ones that we can process. This function is used by the [parser.py](parser.py) when deciding which urls to queue up to be processed. 


### Things I'd do if I had the time or needed to scale up the solution

- Add an option parameter to be passed into the program to control the number of worker tasks to be spawned. Just now it's just a hardcoded value. 
- Update [client.py](clients/client.py) to handle retries when we receive certain status codes or connection errors. 
- Add better exception handling and input validation. 
- Handle dynamic content being returned from a get request
- Add unit tests
- Detecting redirects when fetching the url. 
- If the design needed to scale, look at switching the design to a webserver to database backing or even redesigning to more of a distributed web crawler. 
- If the design needed to be updated to handle multipe domain, update the program to handle a list of urls and update [main.py](main.py) to create a crawler for each url and run them using something like [asyncio.gather](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather). Then update the [parser.py process function](parser.py) to return the output dict rather than print it so that the [main.py](main.py) can handle the outputs

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@2014klee, @danyal-zego, @bogdangoie, @cypherlou and @marliechiller) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.
